"""Archive (tar/zip) fetcher implementation.

Archives are a retrieval strategy alongside git and svn.  They represent
dependencies distributed as ``.tar.gz``, ``.tgz``, ``.tar.bz2``,
``.tar.xz``, or ``.zip`` files reachable via ``http://``, ``https://``,
or ``file://`` URLs.

Unlike VCS sources, archives have no branching or tagging concept.  Version
identity is expressed through:

* **No hash** — the URL itself acts as the identity.
* **``integrity.hash: <algorithm>:<hex>``** — the cryptographic hash of the
  archive file acts as the version identifier.

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

import pathlib
from collections.abc import Sequence

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.metadata import Dependency
from dfetch.util.util import temp_file
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


class ArchiveFetcher:
    """Fetcher for tar/zip archive URLs.

    Archives are identified by URL or cryptographic hash — not by VCS concepts
    such as branches or revisions.  This fetcher implements only the common
    :class:`~dfetch.project.fetcher.Fetcher` protocol.
    """

    NAME: str = "archive"

    def __init__(self, remote: str) -> None:
        """Create an ArchiveFetcher for *remote*."""
        self._remote = remote
        self._remote_repo = ArchiveRemote(remote)

    @classmethod
    def handles(cls, remote: str) -> bool:
        """Return True when *remote* looks like an archive URL."""
        return is_archive_url(remote)

    def wanted_version(self, project_entry: ProjectEntry) -> Version:
        """Version derived from ``integrity.hash`` or the archive URL.

        * With hash → ``Version(revision='<alg>:<hex>')``
        * Without hash → ``Version(revision=<url>)``
        """
        if project_entry.hash:
            return Version(revision=project_entry.hash)
        return Version(revision=self._remote)

    def latest_available_version(self, wanted: Version) -> Version | None:
        """Return *wanted* if the archive URL is still reachable, else None."""
        return wanted if self._remote_repo.is_accessible() else None

    def fetch(
        self,
        version: Version,
        local_path: str,
        name: str,
        source: str,
        ignore: Sequence[str],
    ) -> tuple[Version, list[Dependency]]:
        """Download and extract the archive to *local_path*.

        Raises:
            RuntimeError: On download failure or hash mismatch.
        """
        pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)

        with temp_file(_suffix_for_url(self._remote)) as tmp_path:
            self._download_and_verify(version.revision, tmp_path, name)
            ArchiveLocalRepo.extract(
                tmp_path,
                local_path,
                src=source,
                ignore=ignore,
            )

        return version, []

    def _download_and_verify(self, revision: str, tmp_path: str, name: str) -> None:
        expected = IntegrityHash.parse(revision)
        if expected:
            actual_hex = self._remote_repo.download(
                tmp_path, algorithm=expected.algorithm
            )
            if not expected.matches(actual_hex):
                raise RuntimeError(
                    f"Hash mismatch for {name}! "
                    f"{expected.algorithm} expected {expected.hex_digest}"
                )
        else:
            self._remote_repo.download(tmp_path)

    def freeze(
        self, project: ProjectEntry, on_disk_version: Version | None
    ) -> str | None:
        """Pin *project* to a cryptographic hash of the archive.

        If already hash-pinned, the on-disk hash is reused.  Otherwise the
        archive is downloaded and its SHA-256 is computed.

        Raises:
            RuntimeError: On download or hash-computation failure.
        """
        if not on_disk_version:
            return None
        pinned = IntegrityHash.parse(on_disk_version.revision) or (
            self._download_and_compute_hash("sha256", url=on_disk_version.revision)
        )
        new_hash = str(pinned)
        if project.hash == new_hash:
            return None
        project.hash = new_hash
        return new_hash

    def _download_and_compute_hash(
        self, algorithm: str = "sha256", url: str | None = None
    ) -> IntegrityHash:
        """Download the archive and return its :class:`IntegrityHash`."""
        effective_url = url if url is not None else self._remote
        remote = ArchiveRemote(effective_url) if url is not None else self._remote_repo
        with temp_file(_suffix_for_url(effective_url)) as tmp_path:
            hex_digest = remote.download(tmp_path, algorithm=algorithm)
            return IntegrityHash(algorithm, hex_digest)

    @staticmethod
    def list_tool_info() -> None:
        """No external tool required; archive fetching uses Python stdlib only."""
