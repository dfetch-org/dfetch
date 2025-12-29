"""Git specific implementation."""

import os
import pathlib
from collections.abc import Sequence
from functools import lru_cache
from typing import Optional

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.vcs import VCS
from dfetch.util.util import safe_rmtree
from dfetch.vcs.git import GitLocalRepo, GitRemote, get_git_version

logger = get_logger(__name__)


class GitRepo(VCS):
    """A git repository."""

    NAME = "git"

    def __init__(self, project: ProjectEntry):
        """Create a Git project."""
        super().__init__(project)
        self._remote_repo = GitRemote(self.remote)
        self._local_repo = GitLocalRepo(self.local_path)

    def check(self) -> bool:
        """Check if is GIT."""
        return bool(self._remote_repo.is_git())

    def _latest_revision_on_branch(self, branch: str) -> str:
        """Get the latest revision on a branch."""
        return str(self._remote_repo.last_sha_on_branch(branch))

    def _does_revision_exist(self, revision: str) -> bool:
        """Check if the given revision exists."""
        return self._remote_repo.check_version_exists(revision)

    def _list_of_tags(self) -> list[str]:
        """Get list of all available tags."""
        return [str(tag) for tag in self._remote_repo.list_of_tags()]

    def metadata_revision(self) -> str:
        """Get the revision of the metadata file."""
        return str(self._local_repo.get_last_file_hash(self.metadata_path))

    def current_revision(self) -> str:
        """Get the revision of the metadata file."""
        return str(self._local_repo.get_current_hash())

    def get_diff(
        self, old_revision: str, new_revision: Optional[str], ignore: Sequence[str]
    ) -> str:
        """Get the diff of two revisions."""
        diff_since_revision = str(
            self._local_repo.create_diff(old_revision, new_revision, ignore)
        )

        if new_revision:
            return diff_since_revision

        combined_diff = []

        if diff_since_revision:
            combined_diff += [diff_since_revision]

        untracked_files_patch = str(self._local_repo.untracked_files_patch(ignore))
        if untracked_files_patch:
            combined_diff += [untracked_files_patch]

        return "\n".join(combined_diff)

    @staticmethod
    def revision_is_enough() -> bool:
        """See if this VCS can uniquely distinguish branch with revision only."""
        return True

    @staticmethod
    def list_tool_info() -> None:
        """Print out version information."""
        try:
            tool, version = get_git_version()
            VCS._log_tool(tool, version)
        except RuntimeError as exc:
            logger.debug(
                f"Something went wrong trying to get the version of git: {exc}"
            )
            VCS._log_tool("git", "<not found in PATH>")

    def _fetch_impl(self, version: Version) -> Version:
        """Get the revision of the remote and place it at the local path."""
        rev_or_branch_or_tag = self._determine_what_to_fetch(version)

        # When exporting a file, the destination directory must already exist
        pathlib.Path(self.local_path).mkdir(parents=True, exist_ok=True)

        license_globs = [f"/{name.lower()}" for name in self.LICENSE_GLOBS] + [
            f"/{name.upper()}" for name in self.LICENSE_GLOBS
        ]

        fetched_sha = self._local_repo.checkout_version(
            remote=self.remote,
            version=rev_or_branch_or_tag,
            src=self.source,
            must_keeps=license_globs,
            ignore=self.ignore,
        )

        safe_rmtree(os.path.join(self.local_path, self._local_repo.METADATA_DIR))

        return self._determine_fetched_version(version, fetched_sha)

    def _determine_what_to_fetch(self, version: Version) -> str:
        """Based on asked version, target to fetch."""
        if version.revision and 0 < len(version.revision) < 40:
            raise RuntimeError(
                "Shortened revisions (SHA) in manifests cannot be used,"
                " use complete revision or a branch (or tags instead)"
            )

        return (
            version.revision
            or version.tag
            or version.branch
            or self._remote_repo.get_default_branch()
        )

    def _determine_fetched_version(self, version: Version, fetched_sha: str) -> Version:
        """Based on asked & fetched version, determine info of fetched version."""
        branch = version.branch or self.get_default_branch()
        if version.tag:
            return Version(tag=version.tag, branch=branch)

        return Version(
            branch=branch,
            revision=version.revision or fetched_sha,
        )

    @lru_cache
    def get_default_branch(self) -> str:  # type:ignore
        """Get the default branch of this repository."""
        return self._remote_repo.get_default_branch()
