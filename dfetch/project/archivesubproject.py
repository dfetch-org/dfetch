"""Archive (tar/zip) specific implementation.

Archives are a third VCS type alongside ``git`` and ``svn``.  They represent
versioned dependencies that are distributed as ``.tar.gz``, ``.tgz``,
``.tar.bz2``, ``.tar.xz`` or ``.zip`` files reachable via any URL that Python's
:mod:`urllib.request` understands (``http://``, ``https://``, ``file://``, …).

Unlike git and SVN, archives have no inherent "branching" or "tagging"
concept.  Version identity is expressed through:

* **No hash** – the URL itself acts as the identity.  The archive is
  considered up-to-date as long as the same URL is still reachable.
* **``integrity.hash: <algorithm>:<hex>``** – the cryptographic hash of the
  archive file acts as the version identifier.  The fetch step verifies the
  downloaded archive against this hash and raises an error on mismatch.

The ``integrity:`` block is designed for future extension: ``sig:`` and
``sig-key:`` fields for detached signature / signing-key verification will
slot in alongside ``hash:`` without breaking existing manifests.
Only ``sha256`` is supported today.

Example manifest entries::

    projects:
      # URL-pinned (no integrity check)
      - name: my-headers
        url: https://example.com/my-headers-latest.tar.gz
        vcs: archive

      # Hash-pinned (integrity verified on every fetch)
      - name: my-library
        url: https://example.com/releases/my-library-1.0.tar.gz
        vcs: archive
        integrity:
          hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

.. scenario-include:: ../features/fetch-archive.feature
"""

from __future__ import annotations

import os
import pathlib
import tempfile

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.subproject import SubProject
from dfetch.vcs.archive import (
    SUPPORTED_HASH_ALGORITHMS,
    ArchiveLocalRepo,
    ArchiveRemote,
    _safe_compare_hex,  # private helper, intentionally imported for internal use
    _suffix_for_url,    # private helper, intentionally imported for internal use
    compute_hash,
    is_archive_url,
)

logger = get_logger(__name__)


class ArchiveSubProject(SubProject):
    """A project fetched from a tar/zip archive URL.

    Supports ``src:`` (sub-path extraction), ``ignore:`` (file exclusion) and
    ``patch:`` (local patches applied after every fetch) in the same way as
    the git and SVN implementations.
    """

    NAME = "archive"

    def __init__(self, project: ProjectEntry) -> None:
        """Create an ArchiveSubProject."""
        super().__init__(project)
        self._project_entry = project
        self._remote_repo = ArchiveRemote(project.remote_url)

    # ------------------------------------------------------------------
    # SubProject abstract interface
    # ------------------------------------------------------------------

    def check(self) -> bool:
        """Return *True* when the project URL looks like an archive."""
        return is_archive_url(self.remote)

    @staticmethod
    def revision_is_enough() -> bool:
        """Archives are uniquely identified by their hash (or URL), so yes."""
        return True

    @staticmethod
    def list_tool_info() -> None:
        """Log information about the archive fetching tool (Python's urllib)."""
        import urllib.request as _ur  # noqa: PLC0415

        SubProject._log_tool("urllib", _ur.__doc__ or "built-in")

    def get_default_branch(self) -> str:
        """Archives have no branches; return an empty string."""
        return ""

    def _latest_revision_on_branch(self, branch: str) -> str:  # noqa: ARG002
        """For archives the 'latest revision' is always the URL (or hash)."""
        return self._project_entry.remote_url

    def _download_and_compute_hash(self, algorithm: str = "sha256") -> str:
        """Download the archive to a temporary file and return its hash.

        The temporary file is always cleaned up, even on error.

        Raises:
            RuntimeError: On download failure or unsupported algorithm.
        """
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=_suffix_for_url(self._project_entry.remote_url), delete=False
            ) as tmp:
                tmp_path = tmp.name
            self._remote_repo.download(tmp_path)
            return compute_hash(tmp_path, algorithm)
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def _does_revision_exist(self, revision: str) -> bool:
        """Check whether *revision* (a hash or URL string) is still valid.

        * If *revision* starts with a known hash algorithm prefix (e.g.
          ``sha256:``) **the entire archive is downloaded** to a temporary file
          and its hash is verified against *revision*.  This is intentionally
          thorough — a lightweight HEAD check cannot confirm content integrity.
        * Otherwise *revision* is treated as the URL itself and a lightweight
          reachability check is performed via :meth:`ArchiveRemote.is_accessible`.
        """
        for algo in SUPPORTED_HASH_ALGORITHMS:
            if revision.startswith(f"{algo}:"):
                expected_hex = revision.split(":", 1)[1]
                try:
                    actual = self._download_and_compute_hash(algo)
                    return _safe_compare_hex(actual, expected_hex)
                except RuntimeError:
                    return False

        # revision is the URL – just check accessibility
        return self._remote_repo.is_accessible()

    def _list_of_tags(self) -> list[str]:
        """Archives have no tags; returns an empty list."""
        return []

    # ------------------------------------------------------------------
    # Version overrides
    # ------------------------------------------------------------------

    @property
    def wanted_version(self) -> Version:
        """Version derived from the ``integrity.hash`` field or the archive URL.

        * With ``integrity.hash: sha256:<hex>`` → ``Version(revision='sha256:<hex>')``
        * Without hash → ``Version(revision=<url>)``

        This makes the standard :class:`~dfetch.project.subproject.SubProject`
        comparison machinery work transparently for archives.
        """
        if self._project_entry.hash:
            return Version(revision=self._project_entry.hash)
        return Version(revision=self._project_entry.remote_url)

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def _fetch_impl(self, version: Version) -> Version:
        """Download and extract the archive to the local destination.

        1. Download the archive to a temporary file.
        2. If ``integrity.hash`` is specified, verify the downloaded file.
        3. Extract to :attr:`local_path`, respecting ``src:`` and ``ignore:``.

        Raises:
            RuntimeError: On download failure or hash mismatch.

        Returns:
            The version that was actually fetched (hash string or URL).
        """
        url = self._project_entry.remote_url
        expected_hash = self._project_entry.hash

        pathlib.Path(self.local_path).mkdir(parents=True, exist_ok=True)

        suffix = _suffix_for_url(url)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self._remote_repo.download(tmp_path)

            if expected_hash:
                if ":" not in expected_hash:
                    raise RuntimeError(
                        f"Malformed integrity.hash for {self._project_entry.name!r}: "
                        f"expected '<algorithm>:<hex>', got {expected_hash!r}"
                    )
                algorithm, expected_hex = expected_hash.split(":", 1)
                actual_hex = compute_hash(tmp_path, algorithm)
                if not _safe_compare_hex(actual_hex, expected_hex):
                    raise RuntimeError(
                        f"Hash mismatch for {self._project_entry.name}! "
                        f"{algorithm} expected {expected_hex}"
                    )

            ArchiveLocalRepo.extract(
                tmp_path,
                self.local_path,
                src=self.source,
                ignore=self.ignore,
            )
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        if expected_hash:
            return Version(revision=expected_hash)
        return Version(revision=url)

    # ------------------------------------------------------------------
    # Freeze support
    # ------------------------------------------------------------------

    def freeze_project(self, project: ProjectEntry) -> str | None:
        """Pin *project* to a cryptographic hash of the archive.

        * If the archive was already fetched with a hash, the on-disk revision
          (``sha256:<hex>``) is written to ``integrity.hash`` in the manifest.
        * If the archive was fetched without a hash (URL-only), the archive is
          downloaded again, its SHA-256 is computed, and the result is written
          to ``integrity.hash``.  This ensures the manifest always ends up
          pinned to a specific content fingerprint.

        Returns:
            The ``sha256:<hex>`` string written to *project*, or *None* if the
            manifest was already up-to-date.

        Raises:
            RuntimeError: On download or hash-computation failure so the caller
                can log a meaningful error rather than silently claiming the
                project is already pinned.
        """
        on_disk = self.on_disk_version()
        if not on_disk:
            return None

        revision = on_disk.revision

        # Already hash-pinned – revision is "sha256:<hex>"
        if revision.startswith(tuple(f"{a}:" for a in SUPPORTED_HASH_ALGORITHMS)):
            if project.hash == revision:
                return None
            project.hash = revision
            return revision

        # URL-pinned: download the archive now and compute its hash.
        # Raises RuntimeError on failure so the caller (freeze.py) can log it.
        hex_value = self._download_and_compute_hash("sha256")
        new_hash = f"sha256:{hex_value}"
        if project.hash == new_hash:
            return None
        project.hash = new_hash
        return new_hash
