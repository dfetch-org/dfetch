"""Archive (tar/zip) VCS implementation.

Supports fetching dependencies distributed as ``.tar.gz``, ``.tgz``,
``.tar.bz2``, ``.tar.xz`` or ``.zip`` archives from any URL that Python's
:mod:`urllib.request` can reach (``http://``, ``https://``, ``file://``, …).

Optional integrity checking is supported via an ``integrity:`` manifest block.
The ``hash:`` sub-field (e.g. ``sha256:<hex>``) is supported today; the block
is designed to grow with ``sig:`` and ``sig-key:`` fields for detached
signature / signing-key verification in the future.

Example manifest entry::

    projects:
      - name: my-library
        url: https://example.com/releases/my-library-1.0.tar.gz
        vcs: archive
        integrity:
          hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

"""

from __future__ import annotations

import hashlib
import http.client
import os
import pathlib
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import zipfile
from collections.abc import Sequence
from typing import overload

from dfetch.log import get_logger
from dfetch.util.util import (
    copy_directory_contents,
    copy_src_subset,
    prune_files_by_pattern,
)

#: Archive file extensions recognised by DFetch.
ARCHIVE_EXTENSIONS = (".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".zip")

#: Hash algorithms supported by the ``integrity.hash`` manifest field.
SUPPORTED_HASH_ALGORITHMS = ("sha256",)

logger = get_logger(__name__)

# Safety limits applied during extraction to prevent decompression bombs.
_MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024  # 500 MB
_MAX_MEMBER_COUNT = 10_000


def _http_conn(scheme: str, netloc: str, timeout: int) -> http.client.HTTPConnection:
    """Return an :class:`http.client.HTTPConnection` or HTTPS variant for *netloc*."""
    if scheme == "https":
        return http.client.HTTPSConnection(netloc, timeout=timeout)
    return http.client.HTTPConnection(netloc, timeout=timeout)


def _resource_path(parsed: urllib.parse.ParseResult) -> str:
    """Return the path + query portion of *parsed* suitable for HTTP requests."""
    path = parsed.path or "/"
    return f"{path}?{parsed.query}" if parsed.query else path


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

        * ``file://`` URLs are checked with :func:`os.path.exists` directly —
          no network round-trip needed.
        * ``http``/``https`` URLs first try a ``HEAD`` request.  If the server
          rejects it (405/501) a partial ``GET`` (``Range: bytes=0-0``) is
          attempted instead.  Returns *False* on any final failure.
        * Any other URL scheme returns *False*.
        """
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme == "file":
            return os.path.exists(parsed.path)
        if parsed.scheme not in ("http", "https"):
            return False
        return self._is_http_reachable(parsed)

    def _is_http_reachable(self, parsed: urllib.parse.ParseResult) -> bool:
        """Try HEAD then partial-GET to confirm an HTTP/HTTPS URL is reachable."""
        netloc, path = parsed.netloc, _resource_path(parsed)
        for method, headers in [("HEAD", {}), ("GET", {"Range": "bytes=0-0"})]:
            try:
                conn = _http_conn(parsed.scheme, netloc, timeout=15)
                try:
                    conn.request(method, path, headers=headers)
                    status = conn.getresponse().status
                    if status not in (405, 501):
                        return status < 400
                finally:
                    conn.close()
            except (OSError, ValueError, http.client.HTTPException):
                return False
        return False

    @overload
    def download(self, dest_path: str, algorithm: str) -> str: ...
    @overload
    def download(self, dest_path: str, algorithm: None = ...) -> None: ...

    def download(self, dest_path: str, algorithm: str | None = None) -> str | None:
        """Download the archive to *dest_path*, optionally computing its hash.

        When *algorithm* is given the hash is computed during the download
        stream (zero extra file reads) and the hex digest is returned.

        Args:
            dest_path: Local file path to write the archive to.
            algorithm: Hash algorithm name (e.g. ``"sha256"``).  When *None*
                no hash is computed and *None* is returned.

        Returns:
            Hex digest string when *algorithm* is provided, else *None*.

        Raises:
            RuntimeError: On download failure or unsupported URL scheme.
        """
        hasher = hashlib.new(algorithm) if algorithm else None
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme == "file":
            try:
                if hasher:
                    with open(parsed.path, "rb") as src, open(dest_path, "wb") as dst:
                        for chunk in iter(lambda: src.read(65536), b""):
                            dst.write(chunk)
                            hasher.update(chunk)
                else:
                    shutil.copy(parsed.path, dest_path)
            except OSError as exc:
                raise RuntimeError(
                    f"'{self.url}' is not a valid URL or unreachable: {exc}"
                ) from exc
        elif parsed.scheme in ("http", "https"):
            self._http_download(parsed, dest_path, hasher=hasher)
        else:
            raise RuntimeError(
                f"'{self.url}' uses unsupported scheme '{parsed.scheme}'."
            )
        return hasher.hexdigest() if hasher else None

    def _http_download(
        self,
        parsed: urllib.parse.ParseResult,
        dest_path: str,
        hasher: hashlib._Hash | None = None,
    ) -> None:
        """Download an HTTP/HTTPS resource to *dest_path*.

        When *hasher* is provided each chunk is fed into it during streaming,
        so the caller gets the hash without an extra file read.
        """
        conn = _http_conn(parsed.scheme, parsed.netloc, timeout=60)
        try:
            conn.request("GET", _resource_path(parsed))
            resp = conn.getresponse()
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status} when downloading '{self.url}'")
            with open(dest_path, "wb") as fh:
                while chunk := resp.read(65536):
                    fh.write(chunk)
                    if hasher:
                        hasher.update(chunk)
        except (OSError, http.client.HTTPException) as exc:
            raise RuntimeError(
                f"'{self.url}' is not a valid URL or unreachable: {exc}"
            ) from exc
        finally:
            conn.close()


class ArchiveLocalRepo:
    """Extracts an archive to a local destination directory.

    Supports ``.tar.gz``, ``.tgz``, ``.tar.bz2``, ``.tar.xz`` and ``.zip``
    archives.  A single top-level directory in the archive is automatically
    stripped (like ``tar --strip-components=1``), so the archive may be
    structured as ``project-1.0/src/…`` or ``src/…`` - both work.
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
            top_entries = os.listdir(tmp_dir)
            if len(top_entries) == 1 and os.path.isdir(
                os.path.join(tmp_dir, top_entries[0])
            ):
                extract_root = os.path.join(tmp_dir, top_entries[0])
            else:
                extract_root = tmp_dir

            pathlib.Path(dest_dir).mkdir(parents=True, exist_ok=True)

            if src:
                copy_src_subset(extract_root, dest_dir, src.rstrip("/"), is_license)
            else:
                copy_directory_contents(extract_root, dest_dir)

            if ignore:
                prune_files_by_pattern(dest_dir, ignore)

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
    def check_zip_members(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
        """Validate all ZIP member paths against path-traversal attacks.

        Returns:
            The validated list of members, safe to pass to
            :meth:`zipfile.ZipFile.extract`.

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
        return members

    @staticmethod
    def _check_tar_members(tf: tarfile.TarFile) -> None:
        """Validate TAR members against decompression bombs and path traversal.

        Size/count limits mirror :meth:`check_zip_members`.  Path validation
        is defence-in-depth: on Python ≥ 3.11.4 the ``filter="tar"`` passed to
        :meth:`tarfile.TarFile.extractall` also rejects unsafe paths, but we
        check here too so the guard applies on all supported Python versions.

        Raises:
            RuntimeError: When the archive exceeds the size/count limits or
                contains an absolute path or ``..`` component.
        """
        members = tf.getmembers()
        ArchiveLocalRepo._check_archive_limits(
            len(members), sum(m.size for m in members if m.isfile())
        )
        for member in members:
            member_path = pathlib.PurePosixPath(member.name)
            if member_path.is_absolute() or any(
                part == ".." for part in member_path.parts
            ):
                raise RuntimeError(
                    f"Archive contains an unsafe member path: {member.name!r}"
                )

    @staticmethod
    def _extract_raw(archive_path: str, dest_dir: str) -> None:
        """Extract archive contents to *dest_dir* without any filtering.

        Safety checks performed before extraction:

        * TAR: member count and total uncompressed size (decompression bomb).
          Path sanitisation uses the built-in ``filter="tar"`` filter when
          available (Python ≥ 3.11.4 / 3.12), which rejects absolute paths,
          ``..`` components, absolute symlinks, and device files.  On older
          Python releases extraction proceeds without the filter (member-path
          attacks are still blocked by ``_check_tar_members``).
        * ZIP: member path traversal validation (absolute paths and ``..``
          components are rejected) plus member count and size limits.
        """
        lower = archive_path.lower()
        if tarfile.is_tarfile(archive_path) and not lower.endswith(".zip"):
            with tarfile.open(archive_path, "r:*") as tf:
                ArchiveLocalRepo._check_tar_members(tf)
                if sys.version_info >= (3, 11, 4):
                    tf.extractall(dest_dir, filter="tar")  # nosec B202
                else:
                    tf.extractall(dest_dir)  # nosec B202
        elif lower.endswith(".zip") or zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as zf:
                ArchiveLocalRepo.check_zip_members(zf)
                zf.extractall(dest_dir)  # nosec B202
        else:
            raise RuntimeError(
                f"Unsupported archive format: '{archive_path}'. "
                f"Supported formats: {', '.join(ARCHIVE_EXTENSIONS)}"
            )
