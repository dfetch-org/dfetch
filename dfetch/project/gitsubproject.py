"""Git fetcher implementation."""

import pathlib
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.fetcher import AbstractVcsFetcher
from dfetch.project.metadata import Dependency
from dfetch.util.license import LICENSE_GLOBS
from dfetch.util.util import safe_rm
from dfetch.vcs.git import CheckoutOptions, GitLocalRepo, GitRemote
from dfetch.vcs.git_types import Submodule
from dfetch.vcs.patch import PatchType

logger = get_logger(__name__)


class GitFetcher(AbstractVcsFetcher):
    """Fetcher for git repositories."""

    NAME: str = "git"

    def __init__(self, remote: str) -> None:
        """Create a GitFetcher for *remote*."""
        self._remote = remote
        self._remote_repo = GitRemote(remote)
        self._default_branch: str | None = None

    @classmethod
    def handles(cls, remote: str) -> bool:
        """Return True when *remote* is a git repository."""
        return bool(GitRemote(remote).is_git())

    def revision_is_enough(self) -> bool:
        """Git SHAs are globally unique; revision alone identifies a commit."""
        return True

    def get_default_branch(self) -> str:
        """Return the default branch of this repository (cached after first network fetch)."""
        if self._default_branch is None:
            self._default_branch = self._remote_repo.get_default_branch()
        return self._default_branch

    def list_of_tags(self) -> list[str]:
        """Return all tags."""
        return [str(tag) for tag in self._remote_repo.list_of_tags()]

    def list_of_branches(self) -> list[str]:
        """Return all branches."""
        return [str(branch) for branch in self._remote_repo.list_of_branches()]

    def latest_revision_on_branch(self, branch: str) -> str:
        """Return the latest commit SHA on *branch*."""
        return str(self._remote_repo.last_sha_on_branch(branch))

    def does_revision_exist(self, revision: str) -> bool:
        """Return True if *revision* exists on the remote."""
        return self._remote_repo.check_version_exists(revision)

    def browse_tree(
        self, version: str
    ) -> AbstractContextManager[Callable[[str], list[tuple[str, bool]]]]:
        """Return a context manager yielding a directory-listing callable."""
        return self._remote_repo.browse_tree(version)

    def patch_type(self) -> PatchType:
        """Return git patch format."""
        return PatchType.GIT

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
        """Checkout *version* from git and place it at *local_path*."""
        rev_or_branch_or_tag = self._determine_what_to_fetch(version)

        pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)

        license_globs = [f"/{n.lower()}" for n in LICENSE_GLOBS] + [
            f"/{n.upper()}" for n in LICENSE_GLOBS
        ]

        local_repo = GitLocalRepo(local_path)
        fetched_sha, submodules = local_repo.checkout_version(
            CheckoutOptions(
                remote=self._remote,
                version=rev_or_branch_or_tag,
                src=source,
                must_keeps=license_globs + [".gitmodules"],
                ignore=ignore,
            )
        )

        vcs_deps = [self._submodule_dependency(sub, name) for sub in submodules]

        targets = {local_repo.METADATA_DIR, local_repo.GIT_MODULES_FILE}
        for path in pathlib.Path(local_path).rglob("*"):
            if path.name in targets:
                safe_rm(path)

        return self._determine_fetched_version(version, fetched_sha), vcs_deps

    def _submodule_dependency(self, submodule: Submodule, name: str) -> Dependency:
        logger.print_info_line(
            name,
            f'Found & fetched submodule "./{submodule.path}" '
            f" ({submodule.url} @ {Version(tag=submodule.tag, branch=submodule.branch, revision=submodule.sha)})",
        )
        return Dependency(
            remote_url=submodule.url,
            destination=submodule.path,
            branch=submodule.branch,
            tag=submodule.tag,
            revision=submodule.sha,
            source_type="git-submodule",
        )

    def _determine_what_to_fetch(self, version: Version) -> str:
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
        branch = version.branch or self.get_default_branch()
        if version.tag:
            return Version(tag=version.tag, branch=branch)
        return Version(branch=branch, revision=version.revision or fetched_sha)

    @staticmethod
    def list_tool_info() -> None:
        """Print the installed git version."""
        try:
            tool, version = GitLocalRepo.get_tool_version()
            get_logger(__name__).print_report_line(tool, version.strip())
        except RuntimeError as exc:
            logger.debug(
                f"Something went wrong trying to get the version of git: {exc}"
            )
            get_logger(__name__).print_report_line("git", "<not found in PATH>")
