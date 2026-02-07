"""Super project abstraction.

This module provides the SuperProject class which represents the project that
contains the `dfetch.yaml` manifest file (the "super project"). It provides
helpers to query VCS information about that repository (for example whether
it's a git or svn repository).
"""

from __future__ import annotations

import getpass
import os
import pathlib
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.project.subproject import SubProject
from dfetch.util.util import resolve_absolute_path

logger = get_logger(__name__)


@dataclass
class RevisionRange:
    """A revision pair."""

    old: str
    new: str | None


class SuperProject(ABC):
    """Representation of the project containing the manifest.

    A SuperProject is the repository/directory that contains the dfetch
    manifest file. It exposes helpers to determine whether that project is
    managed by git, svn, or is unversioned.
    """

    def __init__(self, manifest: Manifest, root_directory: pathlib.Path) -> None:
        """Create a SuperProject by looking for a manifest file."""
        self._manifest = manifest
        self._root_directory = root_directory

    @property
    def root_directory(self) -> pathlib.Path:
        """Return the directory that contains the manifest file."""
        return self._root_directory

    @property
    def manifest(self) -> Manifest:
        """The manifest of the super project."""
        return self._manifest

    @staticmethod
    @abstractmethod
    def check(path: str | pathlib.Path) -> bool:
        """Check if this path is of the matching VCS."""

    @abstractmethod
    def get_sub_project(self, project: ProjectEntry) -> SubProject | None:
        """Get the subproject in the same vcs type as the superproject."""

    @abstractmethod
    def ignored_files(self, path: str) -> Sequence[str]:
        """Return a list of files that can be ignored in a given path."""

    @abstractmethod
    def has_local_changes_in_dir(self, path: str) -> bool:
        """Check if the superproject has local changes."""

    @abstractmethod
    def get_username(self) -> str:
        """Get the username of the superproject VCS."""

    def _get_username_fallback(self) -> str:
        """Get the username of the superproject VCS."""
        username = ""

        if not username:
            try:
                username = getpass.getuser()
            except (ImportError, KeyError, OSError):
                username = ""
        if not username:
            try:
                username = os.getlogin()
            except OSError:
                username = "unknown"
        return username

    @abstractmethod
    def get_useremail(self) -> str:
        """Get the user email of the superproject VCS."""

    def _get_useremail_fallback(self) -> str:
        """Get the user email of the superproject VCS."""
        username = self.get_username() or "unknown"
        return f"{username}@example.com"

    @abstractmethod
    def get_file_revision(self, path: str | pathlib.Path) -> str:
        """Get the revision of the given file."""

    @staticmethod
    @abstractmethod
    def import_projects() -> Sequence[ProjectEntry]:
        """Import projects from underlying superproject."""

    @abstractmethod
    def diff(
        self,
        path: str | pathlib.Path,
        revisions: RevisionRange,
        ignore: Sequence[str],
        reverse: bool = False,
    ) -> str:
        """Get the diff of two revisions."""


class NoVcsSuperProject(SuperProject):
    """A superproject without any version control."""

    @staticmethod
    def check(path: str | pathlib.Path) -> bool:
        """Check if this path is of the matching VCS."""
        del path  # unused arg
        return True

    def get_sub_project(self, project: ProjectEntry) -> SubProject | None:
        """Get the subproject in the same vcs type as the superproject."""
        return None

    def ignored_files(self, path: str) -> Sequence[str]:
        """Return a list of files that can be ignored in a given path."""
        resolved_path = resolve_absolute_path(path)

        if not resolved_path.is_relative_to(self.root_directory):
            raise RuntimeError(
                f"{resolved_path} not in superproject {self.root_directory}!"
            )

        return []

    def has_local_changes_in_dir(self, path: str) -> bool:
        """Check if the superproject has local changes."""
        return True

    def get_username(self) -> str:
        """Get the username of the superproject VCS."""
        return self._get_username_fallback()

    def get_useremail(self) -> str:
        """Get the user email of the superproject VCS."""
        return self._get_useremail_fallback()

    def get_file_revision(self, path: str | pathlib.Path) -> str:
        """Get the revision of the given file."""
        return ""

    @staticmethod
    def import_projects() -> Sequence[ProjectEntry]:
        """Import projects from underlying superproject."""
        raise RuntimeError(
            "Only git or SVN projects can be imported."
            "Run this command within either a git or SVN repository",
        )

    def diff(
        self,
        path: str | pathlib.Path,
        revisions: RevisionRange,
        ignore: Sequence[str],
        reverse: bool = False,
    ) -> str:
        """Get the diff between two revisions."""
        del path  # unused arg
        del revisions  # unused arg
        del ignore  # unused arg
        del reverse  # unused arg
        return ""
