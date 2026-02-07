"""SVN specific implementation."""

import os
import pathlib
import urllib.parse

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.subproject import SubProject
from dfetch.util.util import (
    find_matching_files,
    find_non_matching_files,
    safe_rm,
)
from dfetch.vcs.patch import PatchInfo
from dfetch.vcs.svn import SvnRemote, SvnRepo, get_svn_version

logger = get_logger(__name__)


class SvnSubProject(SubProject):
    """A svn subproject."""

    NAME = "svn"

    def __init__(self, project: ProjectEntry):
        """Create a Svn subproject."""
        super().__init__(project)
        self._remote_repo = SvnRemote(self.remote)

    def check(self) -> bool:
        """Check if is SVN."""
        return self._remote_repo.is_svn()

    @staticmethod
    def revision_is_enough() -> bool:
        """See if this VCS can uniquely distinguish branch with revision only."""
        return False

    def _latest_revision_on_branch(self, branch: str) -> str:
        """Get the latest revision on a branch."""
        if branch not in (SvnRepo.DEFAULT_BRANCH, "", " "):
            branch = f"branches/{branch}"
        return self._get_revision(branch)

    def _does_revision_exist(self, revision: str) -> bool:
        """Check if the given revision exists."""
        raise NotImplementedError(
            "In SVN only a revision is NOT enough, this should not be called!"
        )

    def _list_of_tags(self) -> list[str]:
        """Get list of all available tags."""
        return self._remote_repo.list_of_tags()

    @staticmethod
    def list_tool_info() -> None:
        """Print out version information."""
        try:
            tool, version = get_svn_version()
            SubProject._log_tool(tool, version)
        except RuntimeError as exc:
            logger.debug(
                f"Something went wrong trying to get the version of svn: {exc}"
            )
            SubProject._log_tool("svn", "<not found in PATH>")

    def _determine_what_to_fetch(self, version: Version) -> tuple[str, str, str]:
        """Based on the given version, determine what to fetch.

        Args:
            version (Version): Version that needs to be fetched

        Raises:
            RuntimeError: Invalid revision

        Returns:
            Tuple[str, str, str]: branch, branch_path, revision
        """
        if version.tag:
            branch_path = f"tags/{version.tag}/"
            branch = ""
        elif version.branch == " ":
            branch_path = ""
            branch = " "
        else:
            branch = version.branch or SvnRepo.DEFAULT_BRANCH
            branch_path = (
                f"branches/{branch}"
                if branch != SvnRepo.DEFAULT_BRANCH
                else SvnRepo.DEFAULT_BRANCH
            )

        branch_path = urllib.parse.quote(branch_path)

        revision = version.revision or self._get_revision(branch_path)

        if not revision.isdigit():
            raise RuntimeError(f"{revision} must be a number for SVN")

        return (branch, branch_path, revision)

    def _remove_ignored_files(self) -> None:
        """Remove any ignored files, whilst keeping license files."""
        for file_or_dir in find_matching_files(self.local_path, self.ignore):
            if not (file_or_dir.is_file() and self.is_license_file(file_or_dir.name)):
                safe_rm(file_or_dir)

    def _fetch_impl(self, version: Version) -> Version:
        """Get the revision of the remote and place it at the local path."""
        branch, branch_path, revision = self._determine_what_to_fetch(version)
        rev_arg = f"--revision {revision}" if revision else ""

        complete_path = "/".join(
            filter(None, [self.remote, branch_path.strip(), self.source])
        ).strip("/")

        # When exporting a file, the destination directory must already exist
        pathlib.Path(os.path.dirname(self.local_path)).mkdir(
            parents=True, exist_ok=True
        )

        complete_path, file_pattern = self._parse_file_pattern(complete_path)

        SvnRepo.export(complete_path, rev_arg, self.local_path)

        if file_pattern:
            for file in find_non_matching_files(self.local_path, (file_pattern,)):
                os.remove(file)
            if not os.listdir(self.local_path):
                logger.warning(
                    f"The 'src:' filter '{self.source}' didn't match any files from '{self.remote}'"
                )

        if self.source:
            root_branch_path = "/".join([self.remote, branch_path]).strip("/")

            for file in SvnSubProject._license_files(root_branch_path):
                dest = (
                    self.local_path
                    if os.path.isdir(self.local_path)
                    else os.path.dirname(self.local_path)
                )
                SvnRepo.export(f"{root_branch_path}/{file}", rev_arg, dest)
                break

        if self.ignore:
            self._remove_ignored_files()

        return Version(tag=version.tag, branch=branch, revision=revision)

    @staticmethod
    def _parse_file_pattern(complete_path: str) -> tuple[str, str]:
        if complete_path.count("*") > 1:
            raise RuntimeError("Only single * supported in 'src:'!")

        glob_filter = ""
        if complete_path.count("*") == 1:
            before, after = complete_path.split("*", maxsplit=1)
            complete_path, before_star = before.rsplit("/", maxsplit=1)
            glob_filter = "*".join([before_star, after])
        return complete_path, glob_filter

    def _get_info(self, branch: str) -> dict[str, str]:
        return SvnRepo.get_info_from_target(f"{self.remote}/{branch}")

    @staticmethod
    def _license_files(url_path: str) -> list[str]:
        return [
            str(license)
            for license in filter(
                SvnSubProject.is_license_file, SvnRepo.files_in_path(url_path)
            )
        ]

    def _get_revision(self, branch: str) -> str:
        return self._get_info(branch)["Revision"]

    def get_default_branch(self) -> str:
        """Get the default branch of this repository."""
        return SvnRepo.DEFAULT_BRANCH

    def create_formatted_patch_header(self, patch_info: PatchInfo) -> str:
        """Create a formatted patch header for the given patch info."""
        return patch_info.to_svn_header()
