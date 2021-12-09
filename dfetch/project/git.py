"""Git specific implementation."""

import os
import pathlib
from typing import List, Optional

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.vcs import VCS
from dfetch.util.util import safe_rmtree
from dfetch.vcs.git import GitLocalRepo, GitRemote, get_git_version

logger = get_logger(__name__)


class GitRepo(VCS):
    """A git repository."""

    DEFAULT_BRANCH = "master"
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

    def _list_of_tags(self) -> List[str]:
        """Get list of all available tags."""
        return [str(tag) for tag in self._remote_repo.list_of_tags()]

    def metadata_revision(self) -> str:
        """Get the revision of the metadata file."""
        return str(self._local_repo.get_last_file_hash(self.metadata_path))

    def current_revision(self) -> str:
        """Get the revision of the metadata file."""
        return str(self._local_repo.get_current_hash())

    def get_diff(self, old_revision: str, new_revision: Optional[str]) -> str:
        """Get the diff of two revisions."""
        return str(self._local_repo.create_diff(old_revision, new_revision))

    @staticmethod
    def revision_is_enough() -> bool:
        """See if this VCS can uniquely distinguish branch with revision only."""
        return True

    @staticmethod
    def list_tool_info() -> None:
        """Print out version information."""
        tool, version = get_git_version()

        VCS._log_tool(tool, version)

    def _fetch_impl(self, version: Version) -> Version:
        """Get the revision of the remote and place it at the local path."""
        rev_or_branch_or_tag = self._determine_what_to_fetch(version)

        # When exporting a file, the destination directory must already exist
        pathlib.Path(self.local_path).mkdir(parents=True, exist_ok=True)

        license_globs = [f"/{name.lower()}" for name in self.LICENSE_GLOBS] + [
            f"/{name.upper()}" for name in self.LICENSE_GLOBS
        ]

        self._local_repo.checkout_version(
            self.remote, rev_or_branch_or_tag, self.source, license_globs
        )

        safe_rmtree(os.path.join(self.local_path, self._local_repo.METADATA_DIR))

        return self._determine_fetched_version(version)

    def _determine_what_to_fetch(self, version: Version) -> str:
        """Based on asked version, target to fetch."""
        if version.revision and 0 < len(version.revision) < 40:
            raise RuntimeError(
                "Shortened revisions (SHA) in manifests cannot be used,"
                " use complete revision or a branch (or tags instead)"
            )

        return version.revision or version.tag or version.branch or self.DEFAULT_BRANCH

    def _determine_fetched_version(self, version: Version) -> Version:
        """Based on asked version, determine info of fetched version."""
        branch = version.branch or self.DEFAULT_BRANCH
        revision = version.revision
        if not version.tag and not version.revision:
            revision = self._remote_repo.last_sha_on_branch(branch)

        return Version(tag=version.tag, revision=revision, branch=branch)
