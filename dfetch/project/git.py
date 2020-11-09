"""Git specific implementation."""

import os
import re
import logging
from typing import Dict, List
from collections import namedtuple

from dfetch.project.vcs import VCS
from dfetch.util.cmdline import run_on_cmdline
from dfetch.util.util import in_directory, safe_rmtree

Submodule = namedtuple(
    "Submodule", ["name", "toplevel", "path", "sha", "url", "branch"]
)


class GitRepo(VCS):
    """A git repository."""

    METADATA_DIR = ".git"
    DEFAULT_BRANCH = "master"

    @staticmethod
    def submodules(logger: logging.Logger) -> List[Submodule]:
        """Get a list of submodules in the current directory."""
        result = run_on_cmdline(
            logger,
            [
                "git",
                "submodule",
                "foreach",
                "--quiet",
                "echo $name $sm_path $sha1 $toplevel",
            ],
        )

        submodules = []
        for line in result.stdout.decode().split("\n"):
            if line:
                name, sm_path, sha, toplevel = line.split(" ")
                url = GitRepo._get_submodule_urls(logger, toplevel)[name]
                branch = GitRepo._guess_branch_of_sha(
                    os.path.join(toplevel, sm_path), sha, logger
                )
                submodules += [
                    Submodule(
                        name=name,
                        toplevel=toplevel,
                        path=sm_path,
                        sha=sha,
                        url=url,
                        branch=branch,
                    )
                ]
        return submodules

    @staticmethod
    def _get_submodule_urls(logger: logging.Logger, toplevel: str) -> Dict[str, str]:

        result = run_on_cmdline(
            logger,
            [
                "git",
                "config",
                "--file",
                toplevel + "/.gitmodules",
                "--get-regexp",
                "url",
            ],
        )

        return {
            str(match.group(1)): str(match.group(2))
            for match in re.finditer(
                r"submodule\.(.*)\.url\s+(.*)", result.stdout.decode()
            )
        }

    @staticmethod
    def _guess_branch_of_sha(repo_path: str, sha: str, logger: logging.Logger) -> str:

        with in_directory(repo_path):
            result = run_on_cmdline(
                logger,
                ["git", "branch", "--contains", sha],
            )

        branches: List[str] = []
        for branch in result.stdout.decode().split("*"):
            branch = branch.strip()

            if branch and "HEAD detached at" not in branch:
                branches.append(branch)

        return branches[0] if len(branches) == 1 else ""

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
