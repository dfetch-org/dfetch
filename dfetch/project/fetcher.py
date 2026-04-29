"""Fetcher protocols and shared VCS base for subproject composition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.metadata import Dependency
from dfetch.util.versions import latest_tag_from_list
from dfetch.vcs.patch import PatchType


@runtime_checkable
class Fetcher(Protocol):
    """How a dependency is retrieved from its remote.

    Implemented by all retrieval strategies: git, svn, and archive.
    """

    NAME: str

    @classmethod
    def handles(cls, remote: str) -> bool:
        """Return True when this fetcher can handle the given remote URL."""

    def fetch(
        self,
        version: Version,
        local_path: str,
        name: str,
        source: str,
        ignore: Sequence[str],
    ) -> tuple[Version, list[Dependency]]:
        """Retrieve *version* and place it at *local_path*."""

    def wanted_version(self, project_entry: ProjectEntry) -> Version:
        """Derive the desired version from the manifest entry."""

    def freeze(
        self, project: ProjectEntry, on_disk_version: Version | None
    ) -> str | None:
        """Pin *project* to *on_disk_version*; return pinned string or None."""

    def latest_available_version(self, wanted: Version) -> Version | None:
        """Return the latest version matching *wanted*, or None if unavailable."""

    @staticmethod
    def list_tool_info() -> None:
        """Print the installed VCS tool version to the report log."""


@runtime_checkable
class VcsFetcher(Fetcher, Protocol):
    """Fetcher with full VCS semantics: branches, tags, revision uniqueness."""

    def revision_is_enough(self) -> bool:
        """Return True when a revision alone uniquely identifies a version."""

    def get_default_branch(self) -> str:
        """Return the default branch name for this repository."""

    def list_of_tags(self) -> list[str]:
        """Return all available tags."""

    def list_of_branches(self) -> list[str]:
        """Return all available branches."""

    def latest_revision_on_branch(self, branch: str) -> str:
        """Return the latest revision on *branch*."""

    def does_revision_exist(self, revision: str) -> bool:
        """Return True if *revision* exists on the remote."""

    def browse_tree(
        self, version: str
    ) -> AbstractContextManager[Callable[[str], list[tuple[str, bool]]]]:
        """Return a context manager yielding a directory-listing callable."""

    def patch_type(self) -> PatchType:
        """Return the patch format used by this VCS."""


class AbstractVcsFetcher(ABC):
    """Shared implementation for VCS-backed fetchers (git and svn).

    Concrete subclasses must implement the abstract leaf methods.
    ``latest_available_version`` and ``freeze`` are implemented here to avoid
    duplication between git and svn.
    """

    @abstractmethod
    def revision_is_enough(self) -> bool:
        """Return True when a revision alone uniquely identifies a version."""

    @abstractmethod
    def get_default_branch(self) -> str:
        """Return the default branch name."""

    @abstractmethod
    def list_of_tags(self) -> list[str]:
        """Return all available tags."""

    @abstractmethod
    def does_revision_exist(self, revision: str) -> bool:
        """Return True if *revision* exists on the remote."""

    @abstractmethod
    def latest_revision_on_branch(self, branch: str) -> str:
        """Return the latest revision on *branch*."""

    def latest_available_version(self, wanted: Version) -> Version | None:
        """Return the latest version matching *wanted*, or None if unavailable."""
        if wanted.tag:
            return self._latest_tag_version(wanted.tag)
        if self._is_revision_only(wanted):
            return self._revision_version_if_exists(wanted.revision)
        branch = self._resolve_branch(wanted.branch)
        revision = self.latest_revision_on_branch(branch)
        return Version(revision=revision, branch=branch) if revision else None

    def _is_revision_only(self, wanted: Version) -> bool:
        return not wanted.branch and bool(wanted.revision) and self.revision_is_enough()

    def _resolve_branch(self, wanted_branch: str) -> str:
        if wanted_branch == " ":
            return ""
        return wanted_branch or self.get_default_branch()

    def _latest_tag_version(self, tag: str) -> Version | None:
        tags = self.list_of_tags()
        if tag not in tags:
            return None
        return Version(tag=latest_tag_from_list(tag, tags))

    def _revision_version_if_exists(self, revision: str) -> Version | None:
        return Version(revision=revision) if self.does_revision_exist(revision) else None

    def freeze(
        self, project: ProjectEntry, on_disk_version: Version | None
    ) -> str | None:
        """Pin *project* to the on-disk version; return pinned string or None."""
        if not on_disk_version:
            return None
        if self._is_already_pinned(project, on_disk_version):
            return None
        project.version = on_disk_version
        return on_disk_version.revision or on_disk_version.tag or str(on_disk_version)

    def _is_already_pinned(
        self, project: ProjectEntry, on_disk_version: Version
    ) -> bool:
        if project.version.tag:
            return project.version.tag == on_disk_version.tag
        if not project.version.revision or not on_disk_version.revision:
            return False
        return (
            project.version.revision == on_disk_version.revision
            and self.revision_is_enough()
        )
