"""Git Super project abstraction.

This module provides the specific GitSuperProject class which represents
a git project that contains the `dfetch.yaml` manifest file (the "super project").
"""

from __future__ import annotations

import os
import pathlib
from collections.abc import Sequence

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.subproject import SubProject
from dfetch.project.superproject import RevisionRange, SuperProject
from dfetch.util.util import resolve_absolute_path
from dfetch.vcs.git import GitLocalRepo

logger = get_logger(__name__)


class GitSuperProject(SuperProject):
    """A git specific superproject."""

    def __init__(self, manifest: Manifest, root_directory: pathlib.Path) -> None:
        """Create a Git Super project."""
        super().__init__(manifest, root_directory)
        self._repo = GitLocalRepo(root_directory)

    @staticmethod
    def check(path: str | pathlib.Path) -> bool:
        """Check if this path is of the matching VCS."""
        return GitLocalRepo(path).is_git()

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
        username = self._repo.get_username()

        if username:
            return username

        return self._get_username_fallback()

    def get_useremail(self) -> str:
        """Get the user email of the superproject VCS."""
        email = self._repo.get_useremail()

        if email:
            return email
        return self._get_useremail_fallback()

    def get_file_revision(self, path: str | pathlib.Path) -> str:
        """Get the revision of the given file."""
        return str(self._repo.get_last_file_hash(str(path)))

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
        diff_since_revision = local_repo.create_diff(
            revisions.old, revisions.new, ignore, reverse
        )

        if revisions.new:
            return diff_since_revision

        combined_diff = []

        if diff_since_revision:
            combined_diff += [diff_since_revision]

        untracked_files_patch = local_repo.untracked_files_patch(ignore)
        if not untracked_files_patch.is_empty():
            if reverse:
                untracked_files_patch.reverse()
            combined_diff += [untracked_files_patch.dump()]

        return "\n".join(combined_diff)
