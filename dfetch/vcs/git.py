"""Git specific implementation."""

import os
import re
import shutil
from collections import namedtuple
from pathlib import PurePath
from typing import Dict, List, Optional, Tuple

from dfetch.log import get_logger
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import in_directory, safe_rmtree

logger = get_logger(__name__)

Submodule = namedtuple(
    "Submodule", ["name", "toplevel", "path", "sha", "url", "branch", "tag"]
)


def get_git_version() -> Tuple[str, str]:
    """Get the name and version of git."""
    result = run_on_cmdline(logger, "git --version")
    tool, version = result.stdout.decode().strip().split("version", maxsplit=1)
    return (str(tool), str(version))


class GitRemote:
    """A remote git repo."""

    def __init__(self, remote: str) -> None:
        """Create a git remote repo."""
        self._remote = remote

    def is_git(self) -> bool:
        """Check if the set url is git."""
        if self._remote.endswith(".git"):
            return True

        try:
            run_on_cmdline(logger, f"git ls-remote --heads {self._remote}")
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    def last_sha_on_branch(self, branch: str) -> str:
        """Get the last sha of a branch."""
        return self._find_sha_of_branch_or_tag(self._ls_remote(self._remote), branch)

    def find_branch_tip_or_tag_from_sha(self, sha: str) -> Tuple[str, str]:
        """Find branch or tag from sha."""
        return self._find_branch_tip_or_tag_from_sha(self._ls_remote(self._remote), sha)

    def list_of_tags(self) -> List[str]:
        """Get list of all available tags."""
        info = self._ls_remote(self._remote)

        return [
            reference.replace("refs/tags/", "")
            for reference, _ in info.items()
            if reference.startswith("refs/tags/")
        ]

    @staticmethod
    def _ls_remote(remote: str) -> Dict[str, str]:

        result = run_on_cmdline(
            logger, f"git ls-remote --heads --tags {remote}"
        ).stdout.decode()

        info = {}
        for line in filter(lambda x: x, result.split("\n")):
            sha, ref = [part.strip() for part in f"{line} ".split("\t", maxsplit=1)]

            # Annotated tag commit (more important)
            if ref.endswith("^{}"):
                info[ref.strip("^{}")] = sha
            elif ref not in info:
                info[ref] = sha
        return info

    @staticmethod
    def _find_sha_of_branch_or_tag(info: Dict[str, str], branch_or_tag: str) -> str:
        """Find SHA of a branch tip or tag."""
        for reference, sha in info.items():
            if reference in [
                f"refs/heads/{branch_or_tag}",
                f"refs/tags/{branch_or_tag}",
            ]:
                return sha
        return ""

    @staticmethod
    def _find_branch_tip_or_tag_from_sha(
        info: Dict[str, str], rev: str
    ) -> Tuple[str, str]:
        """Check all branch tips and tags and see if the sha is one of them."""
        branch, tag = "", ""
        for reference, sha in info.items():
            if sha.startswith(rev):  # Also allow for shorter SHA's
                if reference.startswith("refs/tags/"):
                    tag = reference.replace("refs/tags/", "")
                elif reference.startswith("refs/heads/"):
                    branch = reference.replace("refs/heads/", "")
                break
        return (branch, tag)


class GitLocalRepo:
    """A git repository."""

    METADATA_DIR = ".git"

    def __init__(self, path: str = ".") -> None:
        """Create a local git repo."""
        self._path = path

    def is_git(self) -> bool:
        """Check if is git."""
        try:
            with in_directory(self._path):
                run_on_cmdline(logger, "git status")
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    def checkout_version(
        self,
        remote: str,
        version: str,
        src: Optional[str],
        must_keeps: Optional[List[str]],
    ) -> None:
        """Checkout a specific version from a given remote.

        Args:
            remote (str): Url or path to a remote git repository
            version (str): A target to checkout, can be branch, tag or sha
            src (Optional[str]): Optional path to subdirectory or file in repo
            must_keeps (Optional[List[str]]): Optional list of glob patterns to keep
        """
        with in_directory(self._path):
            run_on_cmdline(logger, "git init")
            run_on_cmdline(logger, f"git remote add origin {remote}")
            run_on_cmdline(logger, "git checkout -b dfetch-local-branch")

            if src:
                run_on_cmdline(logger, "git config core.sparsecheckout true")
                with open(
                    ".git/info/sparse-checkout", "a", encoding="utf-8"
                ) as sparse_checkout_file:
                    sparse_checkout_file.write(
                        "\n".join(list([f"/{src}"] + (must_keeps or [])))
                    )

            run_on_cmdline(logger, f"git fetch --depth 1 origin {version}")
            run_on_cmdline(logger, "git reset --hard FETCH_HEAD")

            if src:
                full_src = src
                if not os.path.isdir(src):
                    src = os.path.dirname(src)

                try:
                    for file_to_copy in os.listdir(src):
                        shutil.move(src + "/" + file_to_copy, ".")
                    safe_rmtree(PurePath(src).parts[0])
                except FileNotFoundError:
                    logger.warning(
                        f"The 'src:' filter '{full_src}' didn't match any files from '{remote}'"
                    )

    def get_last_file_hash(self, path: str) -> str:
        """Get the hash of a specific file."""
        with in_directory(self._path):
            result = run_on_cmdline(
                logger,
                ["git", "log", "-n", "1", "--pretty=format:%H", "--", path],
            )

        return str(result.stdout.decode())

    def get_current_hash(self) -> str:
        """Get the last revision."""
        with in_directory(self._path):
            result = run_on_cmdline(
                logger,
                ["git", "log", "-n", "1", "--pretty=format:%H"],
            )

        return str(result.stdout.decode())

    def create_diff(self, old_hash: str, new_hash: Optional[str]) -> str:
        """Generate a relative diff patch."""
        with in_directory(self._path):
            cmd = [
                "git",
                "diff",
                "--relative",
                "--binary",  # Add binary content
                "--no-ext-diff",  # Don't allow external diff tools
                "--no-color",
                old_hash,
            ]
            if new_hash:
                cmd.append(new_hash)
            result = run_on_cmdline(logger, cmd)

        return str(result.stdout.decode())

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
                url = GitLocalRepo._get_submodule_urls(toplevel)[name]
                branch, tag = GitRemote(url).find_branch_tip_or_tag_from_sha(sha)

                if not (branch or tag):
                    branch = GitLocalRepo(
                        os.path.join(os.getcwd(), sm_path)
                    ).find_branch_containing_sha(sha)

                submodules += [
                    Submodule(
                        name=name,
                        toplevel=toplevel,
                        path=sm_path,
                        sha=sha,
                        url=url,
                        branch=branch,
                        tag=tag,
                    )
                ]

        if not submodules and os.path.isfile(".gitmodules"):
            logger.warning(
                "This repository probably has submodules, "
                "but they might not have been initialized yet. "
                "Try updating them with 'git submodule update --init' and rerun the command."
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

    def find_branch_containing_sha(self, sha: str) -> str:
        """Try to find the branch that contains the given sha."""
        if not os.path.isdir(os.path.join(self._path, GitLocalRepo.METADATA_DIR)):
            return ""

        with in_directory(self._path):
            result = run_on_cmdline(
                logger,
                ["git", "branch", "--contains", sha],
            )

        branches: List[str] = [
            branch.strip()
            for branch in result.stdout.decode().split("*")
            if branch.strip() and "HEAD detached at" not in branch.strip()
        ]

        return "" if not branches else branches[0]
