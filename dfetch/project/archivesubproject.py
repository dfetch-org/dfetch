"""Archive (tar/zip) specific implementation.

Archives are a third VCS type alongside ``git`` and ``svn``.  They represent
versioned dependencies that are distributed as ``.tar.gz``, ``.tgz``,
``.tar.bz2``, ``.tar.xz`` or ``.zip`` files reachable via ``http://``,
``https://``, or ``file://`` URLs.

Unlike git and SVN, archives have no inherent "branching" or "tagging"
concept.  Version identity is expressed through:

* **No hash** - the URL itself acts as the identity.  The archive is
  considered up-to-date as long as the same URL is still reachable.
* **``integrity.hash: <algorithm>:<hex>``** - the cryptographic hash of the
  archive file acts as the version identifier.  The fetch step verifies the
  downloaded archive against this hash and raises an error on mismatch.

The ``integrity:`` block is designed for future extension: ``sig:`` and
``sig-key:`` fields for detached signature / signing-key verification will
slot in alongside ``hash:`` without breaking existing manifests.
Supported hash algorithms: ``sha256``, ``sha384``, and ``sha512``.

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

.. scenario-include:: ../features/freeze-archive.feature
"""

from __future__ import annotations

import http.client
import os
import pathlib
import tempfile

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.subproject import SubProject
from dfetch.vcs.archive import (
    ARCHIVE_EXTENSIONS,
    ArchiveLocalRepo,
    ArchiveRemote,
    is_archive_url,
)
from dfetch.vcs.integrity_hash import IntegrityHash

logger = get_logger(__name__)


def _suffix_for_url(url: str) -> str:
    """Return the archive file suffix for *url* (e.g. ``'.tar.gz'``, ``'.zip'``)."""
    lower = url.lower()
    for ext in sorted(ARCHIVE_EXTENSIONS, key=len, reverse=True):
        if lower.endswith(ext):
            return ext
    return ".archive"


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

    def check(self) -> bool:
        """Return *True* when the project URL looks like an archive."""
        return is_archive_url(self.remote)

    @staticmethod
    def revision_is_enough() -> bool:
        """Archives are uniquely identified by their hash (or URL), so yes."""
        return True

    @staticmethod
    def list_tool_info() -> None:
        """Log information about the archive fetching tool (Python's http.client)."""
        SubProject._log_tool("http.client", http.client.__doc__ or "built-in")

    def get_default_branch(self) -> str:
        """Archives have no branches; return an empty string."""
        return ""

    def _latest_revision_on_branch(self, branch: str) -> str:
        """For archives the 'latest revision' is always the URL (or hash)."""
        del branch
        return self.remote

    def _download_and_compute_hash(self, algorithm: str = "sha256") -> IntegrityHash:
        """Download the archive to a temporary file and return its :class:`IntegrityHash`.

        The hash is computed during the download stream — no extra file read.
        The temporary file is always cleaned up, even on error.

        Raises:
            RuntimeError: On download failure or unsupported algorithm.
        """
        fd, tmp_path = tempfile.mkstemp(suffix=_suffix_for_url(self.remote))
        os.close(fd)
        try:
            hex_digest = self._remote_repo.download(tmp_path, algorithm=algorithm)
            return IntegrityHash(algorithm, hex_digest)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def _does_revision_exist(self, revision: str) -> bool:  # noqa: ARG002
        """Check whether the archive URL is still reachable.

        A lightweight HEAD (or partial-GET) reachability check is used for
        all revision types, including hash-pinned ones.  Full content-integrity
        verification is intentionally deferred to fetch time (``_fetch_impl``),
        keeping ``dfetch check`` fast even for large archives over slow links.
        """
        return self._remote_repo.is_accessible()

    def _list_of_tags(self) -> list[str]:
        """Archives have no tags; returns an empty list."""
        return []

    @property
    def wanted_version(self) -> Version:
        """Version derived from the ``integrity.hash`` field or the archive URL.

        * With ``integrity.hash: <alg>:<hex>`` → ``Version(revision='<alg>:<hex>')``
        * Without hash → ``Version(revision=<url>)``

        This makes the standard :class:`~dfetch.project.subproject.SubProject`
        comparison machinery work transparently for archives.
        """
        if self._project_entry.hash:
            return Version(revision=self._project_entry.hash)
        return Version(revision=self.remote)

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
        revision = version.revision

        pathlib.Path(self.local_path).mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(suffix=_suffix_for_url(self.remote))
        os.close(fd)
        try:
            expected = IntegrityHash.parse(revision)
            if expected:
                actual_hex = self._remote_repo.download(
                    tmp_path, algorithm=expected.algorithm
                )
                if not expected.matches(actual_hex):
                    raise RuntimeError(
                        f"Hash mismatch for {self._project_entry.name}! "
                        f"{expected.algorithm} expected {expected.hex_digest}"
                    )
            else:
                self._remote_repo.download(tmp_path)

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

        return version

    def freeze_project(self, project: ProjectEntry) -> str | None:
        """Pin *project* to a cryptographic hash of the archive.

        * If the archive was already fetched with a hash, the on-disk revision
          (``sha256:<hex>``) is written to ``integrity.hash`` in the manifest.
        * If the archive was fetched without a hash (URL-only), the archive is
          downloaded again, its SHA-256 is computed, and the result is written
          to ``integrity.hash``.  This ensures the manifest always ends up
          pinned to a specific content fingerprint.  SHA-256 is used as the
          default algorithm when no prior hash is present.

        Returns:
            The ``<algorithm>:<hex>`` string written to *project*, or *None* if
            the manifest was already up-to-date.

        Raises:
            RuntimeError: On download or hash-computation failure so the caller
                can log a meaningful error rather than silently claiming the
                project is already pinned.
        """
        on_disk = self.on_disk_version()
        if not on_disk:
            return None

        revision = on_disk.revision

        # Already hash-pinned — use the on-disk revision directly.
        pinned = IntegrityHash.parse(revision) or self._download_and_compute_hash(
            "sha256"
        )
        new_hash = str(pinned)
        if project.hash == new_hash:
            return None
        project.hash = new_hash
        return new_hash
