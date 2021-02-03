"""Git specific implementation."""

import os
import pathlib
import re
import shutil
from collections import namedtuple
from typing import Dict, List

from dfetch.log import get_logger
from dfetch.project.vcs import VCS
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import in_directory, safe_rmtree

logger = get_logger(__name__)

Submodule = namedtuple(
    "Submodule", ["name", "toplevel", "path", "sha", "url", "branch"]
)


class GitRepo(VCS):
    """A git repository."""

    METADATA_DIR = ".git"
    DEFAULT_BRANCH = "master"
    NAME = "git"

    @staticmethod
    def submodules() -> List[Submodule]:
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
                url = GitRepo._get_submodule_urls(toplevel)[name]
                branch = GitRepo._determine_branch_or_tag(
                    url, os.path.join(os.getcwd(), sm_path), sha
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

        if not submodules and os.path.isfile(".gitmodules"):
            logger.warning(
                "This repository probably has submodules, "
                "but they might not have been initialized yet. "
                "Try updating the with 'git submodule update --init' and rerun the command."
            )

        return submodules

    @staticmethod
    def _get_submodule_urls(toplevel: str) -> Dict[str, str]:

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

    def check(self) -> bool:
        """Check if is GIT."""
        if self.remote.endswith(".git"):
            return True

        try:
            run_on_cmdline(logger, f"git ls-remote --heads {self.remote}")
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    @staticmethod
    def check_path(path: str = ".") -> bool:
        """Check if is git."""
        try:
            with in_directory(path):
                run_on_cmdline(logger, "git status")
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    @staticmethod
    def list_tool_info() -> None:
        """Print out version information."""
        result = run_on_cmdline(logger, "git --version")

        tool, version = result.stdout.decode().strip().split("version", maxsplit=1)

        VCS._log_tool(tool, version)

    def _check_impl(self) -> str:
        """Check if a newer version is available on the given branch."""
        info = self._ls_remote(self.remote)
        branch = self.branch or self.DEFAULT_BRANCH

        return self._find_sha_of_branch_or_tag(info, branch)

    def _fetch_impl(self) -> None:
        """Get the revision of the remote and place it at the local path."""
        if 0 < len(self._project.revision) < 40:
            raise RuntimeError(
                "Shortened revisions (SHA) in manifests cannot be used,"
                " use complete revision or a branch (or tags instead)"
            )

        branch_or_tag = self._project.revision or self.branch or self.DEFAULT_BRANCH

        pathlib.Path(self.local_path).mkdir(parents=True, exist_ok=True)

        with in_directory(self.local_path):
            run_on_cmdline(logger, "git init")
            run_on_cmdline(logger, f"git remote add origin {self.remote}")
            run_on_cmdline(logger, "git checkout -b dfetch-local-branch")

            if self._project.source:
                run_on_cmdline(logger, "git config core.sparsecheckout true")
                with open(".git/info/sparse-checkout", "a") as sparse_checkout_file:
                    sparse_checkout_file.write("/" + self._project.source)

            run_on_cmdline(logger, f"git fetch --depth 1 origin {branch_or_tag}")
            run_on_cmdline(logger, "git reset --hard FETCH_HEAD")

            if self._project.source:
                for file_to_copy in os.listdir(self._project.source):
                    shutil.move(self._project.source + "/" + file_to_copy, ".")
                safe_rmtree(self._project.source)

        self._cleanup()

    @staticmethod
    def _ls_remote(remote: str) -> Dict[str, str]:

        result = run_on_cmdline(logger, f"git ls-remote {remote}")

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

        sha = self._metadata.revision
        branch = self._metadata.branch

        if not branch and not sha:
            branch = self.DEFAULT_BRANCH

        info = self._ls_remote(self.remote)
        if branch and not sha:
            sha = self._find_sha_of_branch_or_tag(info, branch)
        elif not branch and sha:
            branch = GitRepo._find_branch_tip_or_tag_from_sha(info, sha)

        self._metadata.fetched(sha, branch)

    @staticmethod
    def _determine_branch_or_tag(url: str, repo_path: str, sha: str) -> str:
        return GitRepo._find_branch_tip_or_tag_from_sha(
            GitRepo._ls_remote(url), sha
        ) or GitRepo._find_branch_in_local_repo_containing_sha(repo_path, sha)

    @staticmethod
    def _find_branch_in_local_repo_containing_sha(repo_path: str, sha: str) -> str:
        if not os.path.isdir(repo_path):
            return ""

        with in_directory(repo_path):
            if not os.path.isdir(GitRepo.METADATA_DIR):
                return ""
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

    @staticmethod
    def _find_sha_of_branch_or_tag(info: Dict[str, str], branch: str) -> str:
        for reference, sha in info.items():
            if reference in [f"refs/heads/{branch}", f"refs/tags/{branch}"]:
                return sha
        return ""

    @staticmethod
    def _find_branch_tip_or_tag_from_sha(info: Dict[str, str], rev: str) -> str:
        """Check all branch tips and tags and see if the sha is one of them."""
        info.pop("HEAD", None)
        for reference, sha in info.items():
            if sha.startswith(rev):  # Also allow for shorter SHA's
                return reference.replace("refs/heads/", "").replace("refs/tags/", "")
        return ""

    def _cleanup(self) -> None:
        path = os.path.join(self.local_path, self.METADATA_DIR)
        safe_rmtree(path)

    def _checkout(self, revision: str) -> None:
        with in_directory(self.local_path):
            cmd = f"git checkout {revision}"
            run_on_cmdline(logger, cmd)
