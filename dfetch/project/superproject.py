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
from dfetch.manifest.parse import find_manifest, parse
from dfetch.manifest.project import ProjectEntry
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.subproject import SubProject
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.util.util import (
    in_directory,
    resolve_absolute_path,
)
from dfetch.vcs.git import GitLocalRepo
from dfetch.vcs.patch import (
    combine_patches,
    create_svn_patch_for_new_file,
    reverse_patch,
)
from dfetch.vcs.svn import SvnRepo

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

    @staticmethod
    def create() -> SuperProject:
        """Create a SuperProject by looking for a manifest file."""
        logger.debug("Looking for manifest")
        manifest_path = find_manifest()

        logger.debug(f"Using manifest {manifest_path}")
        manifest = parse(manifest_path)
        root_directory = resolve_absolute_path(os.path.dirname(manifest.path))
        return SuperProject.type_from_path(root_directory)(manifest, root_directory)

    @staticmethod
    def type_from_path(path: str | pathlib.Path) -> type[SuperProject]:
        """Determine correct VCS type of the superproject in the given path."""
        if GitLocalRepo(path).is_git():
            return GitSuperProject

        if SvnRepo(path).is_svn():
            return SvnSuperProject

        return NoVcsSuperProject

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

    @staticmethod
    def import_projects() -> Sequence[ProjectEntry]:
        """Import projects from underlying superproject."""
        projects: list[ProjectEntry] = []
        toplevel: str = ""
        for submodule in GitLocalRepo.submodules():
            projects.append(
                ProjectEntry(
                    {
                        "name": submodule.name,
                        "revision": submodule.sha,
                        "url": submodule.url,
                        "dst": submodule.path,
                        "branch": submodule.branch,
                        "tag": submodule.tag,
                    }
                )
            )
            logger.info(f"Found {submodule.name}")

            if not toplevel:
                toplevel = submodule.toplevel
            elif toplevel != submodule.toplevel:
                raise RuntimeError(
                    "Recursive submodules not (yet) supported. Check manifest!"
                )

        if os.path.realpath(toplevel) != os.getcwd():
            logger.warning(
                "\n".join(
                    (
                        f'The toplevel directory is in "{toplevel}"',
                        f'Import was done from "{os.getcwd()}"',
                        "All projects paths will be relative to the current directory dfetch is running!",
                    )
                )
            )

        return projects

    def diff(
        self,
        path: str | pathlib.Path,
        revisions: RevisionRange,
        ignore: Sequence[str],
        reverse: bool = False,
    ) -> str:
        """Get the diff of two revisions in the given path."""
        local_repo = GitLocalRepo(path)
        diff_since_revision = str(
            local_repo.create_diff(revisions.old, revisions.new, ignore, reverse)
        )

        if revisions.new:
            return diff_since_revision

        combined_diff = []

        if diff_since_revision:
            combined_diff += [diff_since_revision]

        untracked_files_patch = str(local_repo.untracked_files_patch(ignore))
        if untracked_files_patch:
            if reverse:
                reversed_patch = reverse_patch(untracked_files_patch.encode("utf-8"))
                if not reversed_patch:
                    raise RuntimeError(
                        "Failed to reverse untracked files patch; patch parsing returned empty."
                    )
                untracked_files_patch = reversed_patch
            combined_diff += [untracked_files_patch]

        return "\n".join(combined_diff)


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

    @staticmethod
    def import_projects() -> Sequence[ProjectEntry]:
        """Import projects from underlying superproject."""
        projects: list[ProjectEntry] = []

        for external in SvnRepo(os.getcwd()).externals():
            projects.append(
                ProjectEntry(
                    {
                        "name": external.name,
                        "revision": external.revision,
                        "url": external.url,
                        "dst": external.path,
                        "branch": external.branch,
                        "tag": external.tag,
                        "src": external.src,
                    }
                )
            )
            logger.info(f"Found {external.name}")

        return projects

    def diff(
        self,
        path: str | pathlib.Path,
        revisions: RevisionRange,
        ignore: Sequence[str],
        reverse: bool = False,
    ) -> str:
        """Get the diff between two revisions."""
        repo = SvnRepo(path)
        if reverse:
            if revisions.new:
                revisions.new, revisions.old = revisions.old, revisions.new

        filtered = repo.create_diff(revisions.old, revisions.new, ignore)

        if revisions.new:
            return filtered

        patches: list[bytes] = [filtered.encode("utf-8")] if filtered else []
        with in_directory(path):
            for file_path in repo.untracked_files(".", ignore):
                patch = create_svn_patch_for_new_file(file_path)
                if patch:
                    patches.append(patch.encode("utf-8"))

        patch_str = combine_patches(patches)

        # SVN has no way of producing a reverse working copy patch, reverse ourselves
        if reverse and not revisions.new:
            patch_str = reverse_patch(patch_str.encode("UTF-8"))

        return patch_str


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

    @staticmethod
    def import_projects() -> Sequence[ProjectEntry]:
        """Import projects from underlying superproject."""
        raise RuntimeError(
            "Only git or SVN projects can be imported.",
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
        return ""
