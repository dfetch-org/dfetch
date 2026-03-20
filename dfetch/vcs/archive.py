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
import hmac
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

# Safety limits applied during extraction to prevent decompression bombs.
_MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024  # 500 MB
_MAX_MEMBER_COUNT = 10_000


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


def _safe_compare_hex(actual: str, expected: str) -> bool:
    """Constant-time comparison of two hex digest strings.

    Uses :func:`hmac.compare_digest` to avoid leaking information about the
    expected hash value via timing side-channels.
    """
    return hmac.compare_digest(actual.lower(), expected.lower())


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
            if len(entries) == 1 and os.path.isdir(os.path.join(tmp_dir, entries[0])):
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
    def _check_archive_limits(member_count: int, total_bytes: int) -> None:
        """Enforce decompression-bomb size and count limits.

        Raises:
            RuntimeError: When *member_count* or *total_bytes* exceeds the
                configured safety limits.
        """
        if member_count > _MAX_MEMBER_COUNT:
            raise RuntimeError(
                f"Archive contains {member_count} members which exceeds the "
                f"safety limit of {_MAX_MEMBER_COUNT}."
            )
        if total_bytes > _MAX_UNCOMPRESSED_BYTES:
            raise RuntimeError(
                f"Archive uncompressed size ({total_bytes} bytes) exceeds the "
                f"safety limit of {_MAX_UNCOMPRESSED_BYTES} bytes."
            )

    @staticmethod
    def _check_zip_members(zf: zipfile.ZipFile) -> None:
        """Validate all ZIP member paths against path-traversal attacks.

        Raises:
            RuntimeError: When any member contains an absolute path, a ``..``
                component, or when the archive exceeds the size/count limits.
        """
        members = zf.infolist()
        ArchiveLocalRepo._check_archive_limits(
            len(members), sum(info.file_size for info in members)
        )
        for info in members:
            member_path = pathlib.PurePosixPath(info.filename)
            if member_path.is_absolute() or any(
                part == ".." for part in member_path.parts
            ):
                raise RuntimeError(
                    f"Archive contains an unsafe member path: {info.filename!r}"
                )

    @staticmethod
    def _check_tar_members(tf: tarfile.TarFile) -> None:
        """Validate TAR member count and total size against decompression bombs.

        Raises:
            RuntimeError: When the archive exceeds the size/count limits.
        """
        members = tf.getmembers()
        ArchiveLocalRepo._check_archive_limits(
            len(members), sum(m.size for m in members if m.isfile())
        )

    @staticmethod
    def _extract_raw(archive_path: str, dest_dir: str) -> None:
        """Extract archive contents to *dest_dir* without any filtering.

        Safety checks performed before extraction:

        * TAR: member count and total uncompressed size (decompression bomb).
          Path sanitisation is handled by the built-in ``filter="tar"`` filter
          (available from Python 3.11.4 / 3.12 as a security backport) which
          rejects absolute paths, ``..`` components, absolute symlinks, and
          device files.
        * ZIP: member path traversal validation (absolute paths and ``..``
          components are rejected) plus member count and size limits.
        """
        lower = archive_path.lower()
        if tarfile.is_tarfile(archive_path) and not lower.endswith(".zip"):
            with tarfile.open(archive_path, "r:*") as tf:
                ArchiveLocalRepo._check_tar_members(tf)
                tf.extractall(dest_dir, filter="tar")
        elif lower.endswith(".zip") or zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as zf:
                ArchiveLocalRepo._check_zip_members(zf)
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
