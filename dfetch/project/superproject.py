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

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.parse import find_manifest, parse
from dfetch.manifest.project import ProjectEntry
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.subproject import SubProject
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.util.util import resolve_absolute_path
from dfetch.vcs.git import GitLocalRepo
from dfetch.vcs.svn import SvnRepo

logger = get_logger(__name__)


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

    @staticmethod
    def create() -> SuperProject:
        """Create a SuperProject by looking for a manifest file."""
        logger.debug("Looking for manifest")
        manifest_path = find_manifest()

        logger.debug(f"Using manifest {manifest_path}")
        manifest = parse(manifest_path)
        root_directory = resolve_absolute_path(os.path.dirname(manifest.path))

        if GitLocalRepo(root_directory).is_git():
            return GitSuperProject(manifest, root_directory)

        if SvnRepo(root_directory).is_svn():
            return SvnSuperProject(manifest, root_directory)

        return NoVcsSuperProject(manifest, root_directory)

    @property
    def root_directory(self) -> pathlib.Path:
        """Return the directory that contains the manifest file."""
        return self._root_directory

    @property
    def manifest(self) -> Manifest:
        """The manifest of the super project."""
        return self._manifest

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

    @abstractmethod
    def get_useremail(self) -> str:
        """Get the user email of the superproject VCS."""

    @abstractmethod
    def get_file_revision(self, path: str | pathlib.Path) -> str:
        """Get the revision of the given file."""


class GitSuperProject(SuperProject):
    """A git specific superproject."""

    def get_sub_project(self, project: ProjectEntry) -> SubProject | None:
        """Get the subproject in the same vcs type as the superproject."""
        return GitSubProject(project)

    def ignored_files(self, path: str) -> Sequence[str]:
        """Return a list of files that can be ignored in a given path."""
        resolved_path = resolve_absolute_path(path)

        if not resolved_path.is_relative_to(self.root_directory):
            raise RuntimeError(
                f"{resolved_path} not in superproject {self.root_directory}!"
            )

        return GitLocalRepo.ignored_files(path)

    def has_local_changes_in_dir(self, path: str) -> bool:
        """Check if the superproject has local changes."""
        return GitLocalRepo.any_changes_or_untracked(path)

    def get_username(self) -> str:
        """Get the username of the superproject VCS."""
        username = GitLocalRepo(self.root_directory).get_username()

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

    def get_useremail(self) -> str:
        """Get the user email of the superproject VCS."""
        email = GitLocalRepo(self.root_directory).get_useremail()

        username = self.get_username() or "unknown"
        return email or f"{username}@example.com"

    def get_file_revision(self, path: str | pathlib.Path) -> str:
        """Get the revision of the given file."""
        return str(GitLocalRepo(self.root_directory).get_last_file_hash(str(path)))


class SvnSuperProject(SuperProject):
    """A SVN specific superproject."""

    def get_sub_project(self, project: ProjectEntry) -> SubProject | None:
        """Get the subproject in the same vcs type as the superproject."""
        return SvnSubProject(project)

    def ignored_files(self, path: str) -> Sequence[str]:
        """Return a list of files that can be ignored in a given path."""
        resolved_path = resolve_absolute_path(path)

        if not resolved_path.is_relative_to(self.root_directory):
            raise RuntimeError(
                f"{resolved_path} not in superproject {self.root_directory}!"
            )

        return SvnRepo.ignored_files(path)

    def has_local_changes_in_dir(self, path: str) -> bool:
        """Check if the superproject has local changes."""
        return SvnRepo.any_changes_or_untracked(path)

    def get_username(self) -> str:
        """Get the username of the superproject VCS."""
        username = SvnRepo(self.root_directory).get_username()

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

    def get_useremail(self) -> str:
        """Get the user email of the superproject VCS."""
        username = self.get_username() or "unknown"
        return f"{username}@example.com"

    def get_file_revision(self, path: str | pathlib.Path) -> str:
        """Get the revision of the given file."""
        return str(SvnRepo(self.root_directory).get_last_changed_revision(str(path)))


class NoVcsSuperProject(SuperProject):
    """A superproject without any version control."""

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

    def get_useremail(self) -> str:
        """Get the user email of the superproject VCS."""
        username = self.get_username() or "unknown"
        return f"{username}@example.com"

    def get_file_revision(self, path: str | pathlib.Path) -> str:
        """Get the revision of the given file."""
        return ""
