"""SVN fetcher implementation."""

import os
import pathlib
import urllib.parse
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.fetcher import AbstractVcsFetcher
from dfetch.project.metadata import Dependency
from dfetch.util.license import is_license_file
from dfetch.util.util import (
    find_matching_files,
    find_non_matching_files,
    safe_rm,
)
from dfetch.vcs.patch import PatchType
from dfetch.vcs.svn import SvnRemote, SvnRepo, get_svn_version

logger = get_logger(__name__)


class SvnFetcher(AbstractVcsFetcher):
    """Fetcher for SVN repositories."""

    NAME: str = "svn"

    def __init__(self, remote: str) -> None:
        """Create a SvnFetcher for *remote*."""
        self._remote = remote
        self._remote_repo = SvnRemote(remote)

    @classmethod
    def handles(cls, remote: str) -> bool:
        """Return True when *remote* is an SVN repository."""
        return SvnRemote(remote).is_svn()

    def revision_is_enough(self) -> bool:
        """SVN revisions are not branch-unique; revision alone is insufficient."""
        return False

    def get_default_branch(self) -> str:
        """Return SVN trunk as the default branch."""
        return SvnRepo.DEFAULT_BRANCH

    def list_of_tags(self) -> list[str]:
        """Return all tags."""
        return self._remote_repo.list_of_tags()

    def list_of_branches(self) -> list[str]:
        """Return trunk plus branches found under ``branches/``."""
        return [SvnRepo.DEFAULT_BRANCH, *self._remote_repo.list_of_branches()]

    def latest_revision_on_branch(self, branch: str) -> str:
        """Return the latest revision number on *branch*."""
        if branch not in (SvnRepo.DEFAULT_BRANCH, "", " "):
            branch = f"branches/{branch}"
        return self._get_revision(branch)

    def does_revision_exist(self, revision: str) -> bool:
        """Not supported for SVN; revision requires a branch context."""
        raise NotImplementedError(
            "In SVN only a revision is NOT enough, this should not be called!"
        )

    def browse_tree(
        self, version: str
    ) -> AbstractContextManager[Callable[[str], list[tuple[str, bool]]]]:
        """Return a context manager yielding a directory-listing callable."""
        return self._remote_repo.browse_tree(version)

    def patch_type(self) -> PatchType:
        """Return SVN patch format."""
        return PatchType.SVN

    def wanted_version(self, project_entry: ProjectEntry) -> Version:
        """Derive the desired version from the manifest entry."""
        return Version(
            branch=project_entry.branch,
            tag=project_entry.tag,
            revision=project_entry.revision,
        )

    def fetch(
        self,
        version: Version,
        local_path: str,
        name: str,
        source: str,
        ignore: Sequence[str],
    ) -> tuple[Version, list[Dependency]]:
        """Export *version* from SVN and place it at *local_path*."""
        logger.debug("Fetching SVN dependency: %s", name)
        branch, branch_path, revision = self._determine_what_to_fetch(version)

        complete_path = "/".join(
            filter(None, [self._remote, branch_path.strip(), source])
        ).strip("/")

        pathlib.Path(os.path.dirname(local_path)).mkdir(parents=True, exist_ok=True)

        complete_path, file_pattern = self._parse_file_pattern(complete_path)

        SvnRepo.export(complete_path, revision, local_path)

        if file_pattern:
            self._apply_file_pattern(local_path, file_pattern, source)

        if source:
            self._copy_license_files(local_path, branch_path, revision)

        if ignore:
            self._remove_ignored_files(local_path, ignore)

        return Version(tag=version.tag, branch=branch, revision=revision), []

    def _apply_file_pattern(
        self, local_path: str, file_pattern: str, source: str
    ) -> None:
        for file in find_non_matching_files(local_path, (file_pattern,)):
            os.remove(file)
        if not os.listdir(local_path):
            logger.warning(
                f"The 'src:' filter '{source}' didn't match any files"
                f" from '{self._remote}'"
            )

    def _copy_license_files(
        self, local_path: str, branch_path: str, revision: str
    ) -> None:
        root_branch_path = "/".join([self._remote, branch_path]).strip("/")
        license_files = SvnFetcher._license_files(root_branch_path)
        if license_files:
            dest = (
                local_path if os.path.isdir(local_path) else os.path.dirname(local_path)
            )
            SvnRepo.export(f"{root_branch_path}/{license_files[0]}", revision, dest)

    def _remove_ignored_files(self, local_path: str, ignore: Sequence[str]) -> None:
        for file_or_dir in find_matching_files(local_path, ignore):
            if not (file_or_dir.is_file() and is_license_file(file_or_dir.name)):
                safe_rm(file_or_dir)

    def _resolve_branch_path(self, version: Version) -> tuple[str, str]:
        """Return (branch, raw_branch_path) from version without URL-encoding."""
        if version.tag:
            return "", f"tags/{version.tag}/"
        if version.branch == " ":
            return " ", ""
        branch = version.branch or SvnRepo.DEFAULT_BRANCH
        branch_path = (
            f"branches/{branch}"
            if branch != SvnRepo.DEFAULT_BRANCH
            else SvnRepo.DEFAULT_BRANCH
        )
        return branch, branch_path

    def _determine_what_to_fetch(self, version: Version) -> tuple[str, str, str]:
        """Return (branch, branch_path, revision) for the given version."""
        branch, branch_path = self._resolve_branch_path(version)
        branch_path = urllib.parse.quote(branch_path)
        revision = version.revision or self._get_revision(branch_path)

        if not revision.isdigit():
            raise RuntimeError(f"{revision} must be a number for SVN")

        return branch, branch_path, revision

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
        return SvnRepo.get_info_from_target(f"{self._remote}/{branch}")

    @staticmethod
    def _license_files(url_path: str) -> list[str]:
        return [
            str(license_file)
            for license_file in filter(is_license_file, SvnRepo.files_in_path(url_path))
        ]

    def _get_revision(self, branch: str) -> str:
        return self._get_info(branch)["Revision"]

    @staticmethod
    def list_tool_info() -> None:
        """Print the installed svn version."""
        try:
            tool, version = get_svn_version()
            get_logger(__name__).print_report_line(tool, version.strip())
        except RuntimeError as exc:
            logger.debug(
                f"Something went wrong trying to get the version of svn: {exc}"
            )
            get_logger(__name__).print_report_line("svn", "<not found in PATH>")
