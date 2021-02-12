"""SVN specific implementation."""

import os
import pathlib
import re
from collections import namedtuple
from typing import Dict, List, Tuple

from dfetch.log import get_logger
from dfetch.project.vcs import VCS
from dfetch.project.version import Version
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import in_directory

logger = get_logger(__name__)


External = namedtuple(
    "External", ["name", "toplevel", "path", "revision", "url", "branch", "tag", "src"]
)


class SvnRepo(VCS):
    """A svn repository."""

    DEFAULT_BRANCH = "trunk"
    NAME = "svn"

    @staticmethod
    def externals() -> List[External]:
        """Get list of externals."""
        result = run_on_cmdline(
            logger,
            [
                "svn",
                "propget",
                "svn:externals",
                "-R",
            ],
        )

        repo_root = SvnRepo._get_info_from_target()["Repository Root"]

        externals = []
        for entry in result.stdout.decode().split(os.linesep * 2):

            match = None
            for match in re.finditer(r"([^\s^-]+)\s+-", entry):
                pass
            if match:
                local_path = match.group(1)

            for match in re.finditer(r"([^\s]+)(?:@)(\d+)\s+([^\s]+)", entry):

                url, branch, tag, src = SvnRepo._split_url(match.group(1), repo_root)

                externals += [
                    External(
                        name=match.group(3),
                        toplevel=os.getcwd(),
                        path="/".join(
                            os.path.join(local_path, match.group(3)).split(os.sep)
                        ),
                        revision=match.group(2).strip(),
                        url=url,
                        branch=branch,
                        tag=tag,
                        src=src,
                    )
                ]

        return externals

    @staticmethod
    def _split_url(url: str, repo_root: str) -> Tuple[str, str, str, str]:

        # ../   Relative to the URL of the directory on which the svn:externals property is set
        # ^/    Relative to the root of the repository in which the svn:externals property is versioned
        # //    Relative to the scheme of the URL of the directory on which the svn:externals property is set
        # /     Relative to the root URL of the server on which the svn:externals property is versioned
        url = re.sub(r"^\^", repo_root, url)
        branch = ""
        tag = ""
        src = ""

        for match in re.finditer(
            r"(.*)\/(branches\/[^\/]+|tags\/[^\/]+|trunk)[\/]*(.*)", url
        ):

            url = match.group(1)
            branch = match.group(2) if match.group(2) != SvnRepo.DEFAULT_BRANCH else ""
            src = match.group(3)

        path = branch.split("/")
        if path[0] == "branches":
            branch = path[1]
        elif path[0] == "tags":
            tag = path[1]
            branch = ""

        return (url, branch, tag, src)

    def check(self) -> bool:
        """Check if is SVN."""
        try:
            run_on_cmdline(logger, f"svn info {self.remote}")
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    @staticmethod
    def check_path(path: str = ".") -> bool:
        """Check if is SVN."""
        try:
            with in_directory(path):
                run_on_cmdline(logger, "svn info")
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    @staticmethod
    def revision_is_enough() -> bool:
        """See if this VCS can uniquely distinguish branch with revision only."""
        return False

    def _latest_revision_on_branch(self, branch: str) -> str:
        """Get the latest revision on a branch."""
        return self._get_revision(branch)

    def _list_of_tags(self) -> List[str]:
        """Get list of all available tags."""
        result = run_on_cmdline(logger, f"svn ls {self.remote}/tags")
        return [
            str(tag).strip("/\r") for tag in result.stdout.decode().split("\n") if tag
        ]

    @staticmethod
    def list_tool_info() -> None:
        """Print out version information."""
        result = run_on_cmdline(logger, "svn --version")

        first_line = result.stdout.decode().split("\n")[0]
        tool, version = first_line.replace(",", "").split("version", maxsplit=1)
        VCS._log_tool(tool, version)

    def _fetch_impl(self, version: Version) -> Version:
        """Get the revision of the remote and place it at the local path."""
        if version.tag:
            branch_path = f"tags/{version.tag}/"
            branch = ""
        elif version.branch and version.branch != self.DEFAULT_BRANCH:
            branch_path = f"branches/{version.branch}"
            branch = version.branch
        else:
            branch = branch_path = self.DEFAULT_BRANCH

        revision = version.revision or self._get_revision(branch_path)

        if not revision.isdigit():
            raise RuntimeError(f"{revision} must be a number for SVN")

        rev_arg = f"--revision {revision}" if revision else ""

        complete_path = "/".join([self.remote, branch_path, self.source]).strip("/")

        # When exporting a file, the destination directory must already exist
        pathlib.Path(os.path.dirname(self.local_path)).mkdir(
            parents=True, exist_ok=True
        )

        run_on_cmdline(
            logger, f"svn export --force {rev_arg} {complete_path} {self.local_path}"
        )

        return Version(tag=version.tag, branch=branch, revision=revision)

    def _get_info(self, branch: str) -> Dict[str, str]:
        return self._get_info_from_target(f"{self.remote}/{branch}")

    @staticmethod
    def _get_info_from_target(target: str = "") -> Dict[str, str]:
        result = run_on_cmdline(logger, f"svn info {target}")

        info = {}
        for line in result.stdout.decode().split(os.linesep):
            if line:
                key, value = f"{line} ".split(":", 1)
                info[key.strip()] = value.strip()
        return info

    def _get_revision(self, branch: str) -> str:
        return self._get_info(branch)["Revision"]
