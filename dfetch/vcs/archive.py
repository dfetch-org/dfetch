"""Archive (tar/zip) VCS implementation.

Supports fetching dependencies distributed as ``.tar.gz``, ``.tgz``,
``.tar.bz2``, ``.tar.xz`` or ``.zip`` archives from any URL that Python's
:mod:`urllib.request` can reach (``http://``, ``https://``, ``file://``, …).

Optional integrity checking is supported via an ``integrity:`` manifest block.
The ``hash:`` sub-field accepts ``sha256:<hex>`` (64 hex chars),
``sha384:<hex>`` (96 hex chars), or ``sha512:<hex>`` (128 hex chars).
The block is designed to grow with ``sig:`` and ``sig-key:`` fields for
detached signature / signing-key verification in the future.

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
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Sequence
from typing import overload

from packageurl import PackageURL

from dfetch.log import get_logger
from dfetch.util.util import (
    copy_directory_contents,
    copy_src_subset,
    prune_files_by_pattern,
)
from dfetch.util.versions import coerce

logger = get_logger(__name__)

#: Archive file extensions recognised by DFetch.
ARCHIVE_EXTENSIONS = (".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".zip")

# Safety limits applied during extraction to prevent decompression bombs.
_MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024  # 500 MB
_MAX_MEMBER_COUNT = 10_000


def is_archive_url(url: str) -> bool:
    """Return *True* when *url* ends with a recognised archive extension.

    Query strings and fragments are stripped before testing so that URLs like
    ``https://example.com/pkg.tar.gz?download=1`` are correctly recognised.
    """
    path = urllib.parse.urlparse(url).path
    return any(path.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS)


def strip_archive_extension(name: str) -> str:
    """Remove a recognised archive extension from *name*."""
    lower = name.lower()
    for ext in ARCHIVE_EXTENSIONS:
        if lower.endswith(ext):
            return name[: -len(ext)]
    return name


def archive_url_to_purl(
    download_url: str,
    version: str | None = None,
    subpath: str | None = None,
) -> PackageURL:
    """Build a github or generic PackageURL for an archive download URL."""
    if match := re.search(
        r"https://github\.com/(?P<org>[^/]+)/(?P<repo>[^/]+)/releases/download/(?P<version>[^/]+)/",
        download_url,
    ):
        prefix, current_version, _ = coerce(
            match["version"],
        )
        return PackageURL(
            type="github",
            namespace=match["org"].lower(),
            name=match["repo"].lower(),
            version=str(current_version) or prefix,
        )

    parsed = urllib.parse.urlparse(download_url)
    basename = os.path.basename(parsed.path)
    name = strip_archive_extension(basename) or "unknown"
    namespace = parsed.hostname or ""
    return PackageURL(
        type="generic",
        namespace=namespace or None,
        name=name,
        version=version,
        qualifiers={"download_url": download_url},
        subpath=subpath,
    )


def _http_conn(scheme: str, netloc: str, timeout: int) -> http.client.HTTPConnection:
    """Return an :class:`http.client.HTTPConnection` or HTTPS variant for *netloc*."""
    if scheme == "https":
        return http.client.HTTPSConnection(netloc, timeout=timeout)
    return http.client.HTTPConnection(netloc, timeout=timeout)


def _resource_path(parsed: urllib.parse.ParseResult) -> str:
    """Return the path + query portion of *parsed* suitable for HTTP requests."""
    path = parsed.path or "/"
    return f"{path}?{parsed.query}" if parsed.query else path


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
            try:
                return os.path.exists(urllib.request.url2pathname(parsed.path))
            except urllib.error.URLError:
                return False
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
            file_path = urllib.request.url2pathname(parsed.path)
            try:
                if hasher:
                    with open(file_path, "rb") as src, open(dest_path, "wb") as dst:
                        for chunk in iter(lambda: src.read(65536), b""):
                            dst.write(chunk)
                            hasher.update(chunk)
                else:
                    shutil.copy(file_path, dest_path)
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

    _MAX_REDIRECTS = 10

    @staticmethod
    def _stream_response_to_file(
        resp: http.client.HTTPResponse,
        dest_path: str,
        hasher: hashlib._Hash | None,
    ) -> None:
        """Write the response body to *dest_path*, updating *hasher* for each chunk."""
        with open(dest_path, "wb") as fh:
            while chunk := resp.read(65536):
                fh.write(chunk)
                if hasher:
                    hasher.update(chunk)

    def _http_download(
        self,
        parsed: urllib.parse.ParseResult,
        dest_path: str,
        hasher: hashlib._Hash | None = None,
    ) -> None:
        """Download an HTTP/HTTPS resource to *dest_path*, following redirects.

        Up to :attr:`_MAX_REDIRECTS` 3xx redirects are followed transparently
        (e.g. GitHub archive URLs redirect to a CDN).  When *hasher* is
        provided each chunk is fed into it during streaming, so the caller gets
        the hash without an extra file read.
        """
        for _ in range(self._MAX_REDIRECTS + 1):
            conn = _http_conn(parsed.scheme, parsed.netloc, timeout=60)
            try:
                conn.request("GET", _resource_path(parsed))
                resp = conn.getresponse()
                if resp.status in (301, 302, 303, 307, 308):
                    location = resp.getheader("Location", "")
                    if not location:
                        raise RuntimeError(
                            f"Redirect with no Location header from '{parsed.geturl()}'"
                        )
                    parsed = urllib.parse.urlparse(
                        urllib.parse.urljoin(parsed.geturl(), location)
                    )
                    continue
                if resp.status != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status} when downloading '{self.url}'"
                    )
                self._stream_response_to_file(resp, dest_path, hasher)
                return
            except (OSError, http.client.HTTPException) as exc:
                raise RuntimeError(
                    f"'{self.url}' is not a valid URL or unreachable: {exc}"
                ) from exc
            finally:
                conn.close()
        raise RuntimeError(f"Too many redirects when downloading '{self.url}'")


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
    def _check_archive_member_path(name: str) -> None:
        """Raise *RuntimeError* if *name* is an unsafe archive member path.

        Rejects absolute paths and any ``..`` path component.

        Raises:
            RuntimeError: When *name* is absolute or contains a ``..`` component.
        """
        member_path = pathlib.PurePosixPath(name)
        if member_path.is_absolute() or any(part == ".." for part in member_path.parts):
            raise RuntimeError(f"Archive contains an unsafe member path: {name!r}")

    @staticmethod
    def check_zip_members(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
        """Validate all ZIP member paths against path-traversal attacks.

        Returns:
            The validated list of members, safe to pass to
            :meth:`zipfile.ZipFile.extract`.

        Raises:
            RuntimeError: When any member contains an absolute path, a ``..``
                component, a symlink with an unsafe target, or when the archive
                exceeds the size/count limits.
        """
        members = zf.infolist()
        ArchiveLocalRepo._check_archive_limits(
            len(members), sum(info.file_size for info in members)
        )
        for info in members:
            ArchiveLocalRepo._check_archive_member_path(info.filename)
            ArchiveLocalRepo._check_zip_member_type(info, zf)
        return members

    @staticmethod
    def _is_unsafe_symlink_target(target: str) -> bool:
        r"""Return *True* when *target* is an unsafe symlink destination.

        A target is unsafe if it is absolute or contains ``..`` components
        under either POSIX or Windows path semantics, so that backslash-based
        traversals like ``..\\..\\evil`` are caught on any host OS.
        """
        posix = pathlib.PurePosixPath(target)
        win = pathlib.PureWindowsPath(target)
        return (
            posix.is_absolute()
            or bool(win.anchor)
            or any(part == ".." for part in posix.parts)
            or any(part == ".." for part in win.parts)
        )

    @staticmethod
    def _check_zip_member_type(info: zipfile.ZipInfo, zf: zipfile.ZipFile) -> None:
        """Reject dangerous ZIP member types (mirrors :meth:`_check_tar_member_type`).

        Detects Unix symlinks encoded in the ``external_attr`` high word and
        validates their targets with the same rules applied to TAR symlinks:
        absolute targets and targets containing ``..`` are rejected.

        Raises:
            RuntimeError: When *info* is a symlink with an unsafe target.
        """
        max_symlink_target = 4096
        unix_mode = info.external_attr >> 16
        if stat.S_ISLNK(unix_mode):
            with zf.open(info) as member_file:
                raw = member_file.read(max_symlink_target + 1)
            if len(raw) > max_symlink_target:
                raise RuntimeError(
                    f"Archive contains a symlink with an oversized target: "
                    f"{info.filename!r}"
                )
            target = raw.decode(errors="replace")
            if ArchiveLocalRepo._is_unsafe_symlink_target(target):
                raise RuntimeError(
                    f"Archive contains a symlink with an unsafe target: "
                    f"{info.filename!r} -> {target!r}"
                )

    @staticmethod
    def _check_tar_member_type(member: tarfile.TarInfo) -> None:
        """Reject dangerous TAR member types that could harm the host system.

        On Python ≥ 3.11.4 the ``filter="tar"`` passed to
        :meth:`tarfile.TarFile.extractall` already blocks many of these, but
        we validate here too so the guard is active on **all** supported Python
        versions and provides defence-in-depth on newer ones.

        Rejected member types:

        * **Symlinks with absolute or escaping targets** — could create a
          foothold outside the extraction directory for later writes.
        * **Hard links with absolute or escaping targets** — same risk as
          dangerous symlinks; the target path is validated like a regular
          member name.
        * **Device files** (character, block) — accessing ``/dev/mem`` or
          similar via an extracted device node can compromise the host.
        * **FIFO / named pipes** — rarely present in software archives and
          can be used to communicate with host processes or block extraction.

        Raises:
            RuntimeError: When *member* is a disallowed or unsafe member type.
        """
        if member.issym():
            target = member.linkname
            if ArchiveLocalRepo._is_unsafe_symlink_target(target):
                raise RuntimeError(
                    f"Archive contains a symlink with an unsafe target: "
                    f"{member.name!r} -> {target!r}"
                )
        elif member.islnk():
            # Hard-link targets are archive-relative paths; apply the same
            # path-traversal check as we do for regular member names.
            ArchiveLocalRepo._check_archive_member_path(member.linkname)
        elif member.isdev() or member.isfifo():
            raise RuntimeError(
                f"Archive contains a special file (device/FIFO): {member.name!r}"
            )

    @staticmethod
    def _check_tar_members(tf: tarfile.TarFile) -> None:
        """Validate TAR members against decompression bombs and unsafe member types.

        Checks applied (all supported Python versions):

        * **Size / count limits** — guard against decompression-bomb archives.
        * **Path traversal** — reject absolute paths and ``..`` components.
        * **Unsafe member types** — reject symlinks with absolute or escaping
          targets, hardlinks with escaping targets, device files, and FIFOs
          (see :meth:`_check_tar_member_type`).

        On Python ≥ 3.11.4 the ``filter="tar"`` passed to
        :meth:`tarfile.TarFile.extractall` provides additional OS-level
        protection; these checks remain as defence-in-depth.

        Raises:
            RuntimeError: When the archive exceeds the size/count limits,
                contains an absolute path or ``..`` component, or contains an
                unsafe member type (dangerous symlink, device file, FIFO).
        """
        members = tf.getmembers()
        ArchiveLocalRepo._check_archive_limits(
            len(members), sum(m.size for m in members if m.isfile())
        )
        for member in members:
            ArchiveLocalRepo._check_archive_member_path(member.name)
            ArchiveLocalRepo._check_tar_member_type(member)

    @staticmethod
    def _extract_raw(archive_path: str, dest_dir: str) -> None:
        """Extract archive contents to *dest_dir* without any filtering.

        Safety checks performed before extraction:

        * TAR: :meth:`_check_tar_members` validates every member for
          decompression-bomb limits, path traversal, dangerous symlink
          targets, hardlink targets, device files, and FIFOs on **all**
          supported Python versions.  When Python ≥ 3.11.4 is available the
          built-in ``filter="tar"`` provides additional OS-level enforcement
          as defence-in-depth.
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
