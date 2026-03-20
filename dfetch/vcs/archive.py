"""Archive (tar/zip) VCS implementation.

Supports fetching dependencies distributed as ``.tar.gz``, ``.tgz``,
``.tar.bz2``, ``.tar.xz`` or ``.zip`` archives from any URL that Python's
:mod:`urllib.request` can reach (``http://``, ``https://``, ``file://``, …).

Optional integrity checking is supported via a ``hash:`` manifest field
(e.g. ``hash: sha256:<hex>``).  The ``sha256`` algorithm is supported today;
the format is designed for extension to ``sha512``, ``md5``, etc.

Example manifest entry::

    projects:
      - name: my-library
        url: https://example.com/releases/my-library-1.0.tar.gz
        vcs: archive
        hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

"""

from __future__ import annotations

import hashlib
import io
import os
import pathlib
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Sequence

from dfetch.log import get_logger
from dfetch.project.subproject import SubProject
from dfetch.util.util import find_matching_files, safe_rm

logger = get_logger(__name__)

#: Archive file extensions recognised by DFetch.
ARCHIVE_EXTENSIONS = (".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".zip")

#: Hash algorithms supported by the ``hash:`` manifest field.
SUPPORTED_HASH_ALGORITHMS = ("sha256",)


def is_archive_url(url: str) -> bool:
    """Return *True* when *url* ends with a recognised archive extension."""
    return any(url.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS)


def compute_hash(path: str, algorithm: str = "sha256") -> str:
    """Compute the hex digest of *path* using *algorithm*.

    Args:
        path: Path to the file.
        algorithm: Hash algorithm name (e.g. ``"sha256"``).

    Returns:
        Lowercase hex digest string.

    Raises:
        RuntimeError: When *algorithm* is not supported.
    """
    if algorithm not in SUPPORTED_HASH_ALGORITHMS:
        raise RuntimeError(
            f"Unsupported hash algorithm '{algorithm}'. "
            f"Supported: {', '.join(SUPPORTED_HASH_ALGORITHMS)}"
        )
    h = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class ArchiveRemote:
    """Represents a remote archive (tar/zip) URL.

    Provides helpers to check accessibility and download the archive.
    """

    def __init__(self, url: str) -> None:
        """Create an ArchiveRemote for *url*."""
        self.url = url

    def is_accessible(self) -> bool:
        """Return *True* when the archive URL is reachable.

        Sends a lightweight ``HEAD`` request for ``http``/``https`` URLs and
        tests existence for ``file://`` URLs.  Returns *False* on any network
        or I/O error.
        """
        try:
            parsed = urllib.request.Request(self.url, method="HEAD")
            with urllib.request.urlopen(parsed, timeout=15):
                return True
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def download(self, dest_path: str) -> None:
        """Download the archive to *dest_path*.

        Args:
            dest_path: Local file path to write the archive to.

        Raises:
            RuntimeError: On download failure.
        """
        try:
            urllib.request.urlretrieve(self.url, dest_path)
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(
                f"'{self.url}' is not a valid URL or unreachable: {exc}"
            ) from exc


class ArchiveLocalRepo:
    """Extracts an archive to a local destination directory.

    Supports ``.tar.gz``, ``.tgz``, ``.tar.bz2``, ``.tar.xz`` and ``.zip``
    archives.  A single top-level directory in the archive is automatically
    stripped (like ``tar --strip-components=1``), so the archive may be
    structured as ``project-1.0/src/…`` or ``src/…`` – both work.
    """

    @staticmethod
    def extract(
        archive_path: str,
        dest_dir: str,
        src: str = "",
        ignore: Sequence[str] = (),
        is_license: bool = True,
    ) -> None:
        """Extract *archive_path* into *dest_dir*, applying *src* / *ignore* filters.

        Args:
            archive_path: Path to the downloaded archive file.
            dest_dir: Directory to place the extracted contents into.
            src: Optional sub-directory (or glob pattern) inside the archive
                 to extract exclusively.  License files from the archive root
                 are always retained when *src* is set.
            ignore: Sequence of glob patterns for files/directories to exclude.
            is_license: Whether to check for and retain license files when
                        *src* is specified.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            ArchiveLocalRepo._extract_raw(archive_path, tmp_dir)

            # Strip a single top-level directory if the archive uses one
            entries = os.listdir(tmp_dir)
            if len(entries) == 1 and os.path.isdir(
                os.path.join(tmp_dir, entries[0])
            ):
                extract_root = os.path.join(tmp_dir, entries[0])
            else:
                extract_root = tmp_dir

            pathlib.Path(dest_dir).mkdir(parents=True, exist_ok=True)

            if src:
                ArchiveLocalRepo._copy_with_src(
                    extract_root, dest_dir, src.rstrip("/"), is_license
                )
            else:
                ArchiveLocalRepo._copy_all(extract_root, dest_dir)

            if ignore:
                ArchiveLocalRepo._apply_ignore(dest_dir, ignore)

    @staticmethod
    def _extract_raw(archive_path: str, dest_dir: str) -> None:
        """Extract archive contents to *dest_dir* without any filtering."""
        lower = archive_path.lower()
        if tarfile.is_tarfile(archive_path) and not lower.endswith(".zip"):
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(dest_dir, filter="tar")
        elif lower.endswith(".zip") or zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(dest_dir)
        else:
            raise RuntimeError(
                f"Unsupported archive format: '{archive_path}'. "
                f"Supported formats: {', '.join(ARCHIVE_EXTENSIONS)}"
            )

    @staticmethod
    def _copy_with_src(
        extract_root: str, dest_dir: str, src: str, keep_licenses: bool
    ) -> None:
        """Copy only *src* sub-directory contents (and optionally licenses) to *dest_dir*."""
        src_path = os.path.join(extract_root, src)

        if os.path.isdir(src_path):
            for item in os.listdir(src_path):
                s = os.path.join(src_path, item)
                d = os.path.join(dest_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
        elif os.path.isfile(src_path):
            shutil.copy2(src_path, os.path.join(dest_dir, os.path.basename(src_path)))

        if keep_licenses:
            for item in os.listdir(extract_root):
                full = os.path.join(extract_root, item)
                if os.path.isfile(full) and SubProject.is_license_file(item):
                    shutil.copy2(full, os.path.join(dest_dir, item))

    @staticmethod
    def _copy_all(extract_root: str, dest_dir: str) -> None:
        """Copy all contents of *extract_root* into *dest_dir*."""
        for item in os.listdir(extract_root):
            s = os.path.join(extract_root, item)
            d = os.path.join(dest_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

    @staticmethod
    def _apply_ignore(dest_dir: str, ignore: Sequence[str]) -> None:
        """Remove files/directories matching *ignore* patterns from *dest_dir*."""
        for file_or_dir in find_matching_files(dest_dir, ignore):
            if not (
                file_or_dir.is_file() and SubProject.is_license_file(file_or_dir.name)
            ):
                safe_rm(file_or_dir)


def _suffix_for_url(url: str) -> str:
    """Return the archive file suffix for a URL (e.g. '.tar.gz', '.zip')."""
    lower = url.lower()
    for ext in sorted(ARCHIVE_EXTENSIONS, key=len, reverse=True):
        if lower.endswith(ext):
            return ext
    return ".archive"
