"""Svn Super project abstraction.

This module provides the specific SvnSuperProject class which represents
a svn project that contains the `dfetch.yaml` manifest file (the "super project").
"""

from __future__ import annotations

import os
import pathlib
from collections.abc import Sequence

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.project.subproject import SubProject
from dfetch.project.superproject import RevisionRange, SuperProject
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.util.util import (
    in_directory,
    resolve_absolute_path,
)
from dfetch.vcs.patch import Patch, PatchType
from dfetch.vcs.svn import SvnRepo

logger = get_logger(__name__)


class SvnSuperProject(SuperProject):
    """A SVN specific superproject."""

    def __init__(self, manifest: Manifest, root_directory: pathlib.Path) -> None:
        """Create a Svn Super project."""
        super().__init__(manifest, root_directory)
        self._repo = SvnRepo(root_directory)

    @staticmethod
    def check(path: str | pathlib.Path) -> bool:
        """Check if this path is of the matching VCS."""
        return SvnRepo(path).is_svn()

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
        username = self._repo.get_username()

        if username:
            return username

        return self._get_username_fallback()

    def get_useremail(self) -> str:
        """Get the user email of the superproject VCS."""
        return self._get_useremail_fallback()

    def get_file_revision(self, path: str | pathlib.Path) -> str:
        """Get the revision of the given file."""
        return str(self._repo.get_last_changed_revision(str(path)))

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
        new, old = revisions.new, revisions.old
        if reverse:
            if new:
                new, old = old, new

        patch = repo.create_diff(old, new, ignore)

        if new:
            return patch.dump()

        with in_directory(path):
            patch.extend(
                Patch.for_new_files(repo.untracked_files(".", ignore), PatchType.SVN)
            )

        # SVN has no way of producing a reverse working copy patch, reverse ourselves
        if reverse:
            patch.reverse()

        return patch.dump()
