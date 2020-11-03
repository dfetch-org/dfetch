"""Git specific implementation."""

import os
import logging
from typing import Dict

from dfetch.project.vcs import VCS
from dfetch.util.cmdline import run_on_cmdline
from dfetch.util.util import in_directory, safe_rmtree


class GitRepo(VCS):
    """A git repository."""

    METADATA_DIR = ".git"
    DEFAULT_BRANCH = "master"

    def check(self) -> bool:
        """Check if is GIT."""
        return self._project.remote_url.endswith(".git")

    @staticmethod
    def list_tool_info(logger: logging.Logger) -> None:
        """Print out version information."""
        result = run_on_cmdline(logger, "git --version")

        tool, version = result.stdout.decode().strip().split("version", maxsplit=1)

        VCS._log_tool(logger, tool, version)

    def _check_impl(self) -> str:
        """Check if a newer version is available on the given branch."""
        info = self.__ls_remote()
        branch = self.branch or self.DEFAULT_BRANCH

        return self._find_sha_of_branch_or_tag(info, branch)

    def _fetch_impl(self) -> None:
        """Get the revision of the remote and place it at the local path."""
        # also allow for revision
        branch = self.branch or self.DEFAULT_BRANCH
        cmd = f"git clone --branch {branch} --depth 1 {self.remote} {self.local_path}"

        run_on_cmdline(self.logger, cmd)

        self._cleanup()

    def __ls_remote(self) -> Dict[str, str]:

        result = run_on_cmdline(self.logger, f"git ls-remote {self.remote}")

        info = {}
        for line in result.stdout.decode().split("\n"):
            if line:
                key, value = f"{line} ".split("\t", 1)
                if not value.startswith("refs/pull"):

                    # Annotated tag commit (more important)
                    if value.strip().endswith("^{}"):
                        info[value.strip().strip("^{}")] = key.strip()
                    else:
                        if value.strip() not in info:
                            info[value.strip()] = key.strip()
        return info

    def _update_metadata(self) -> None:

        info = self.__ls_remote()

        rev = self._metadata.revision
        branch = self._metadata.branch

        if not branch and not rev:
            branch = self.DEFAULT_BRANCH

        if branch and not rev:
            rev = self._find_sha_of_branch_or_tag(info, branch)
        elif not branch and rev:
            branch = self._find_branch_or_tag_from_sha(info, rev)

        self._metadata.fetched(rev, branch)

    @staticmethod
    def _find_sha_of_branch_or_tag(info: Dict[str, str], branch: str) -> str:
        for reference, sha in info.items():
            if reference in [f"refs/heads/{branch}", f"refs/tags/{branch}"]:
                return sha
        return ""

    @staticmethod
    def _find_branch_or_tag_from_sha(info: Dict[str, str], rev: str) -> str:
        for reference, sha in info.items():
            if sha[:8] == rev[:8]:  # Also allow for shorter SHA's
                return reference.replace("refs/heads", "").replace("refs/tags", "")
        return ""

    def _cleanup(self) -> None:
        path = os.path.join(self.local_path, self.METADATA_DIR)
        safe_rmtree(path)

    def _checkout(self, revision: str) -> None:
        with in_directory(self.local_path):
            cmd = f"git checkout {revision}"
            run_on_cmdline(self.logger, cmd)
