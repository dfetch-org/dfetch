"""SVN specific implementation."""

import itertools
import os
import pathlib
import re
from collections import namedtuple
from typing import Dict, List, Tuple

from dfetch.log import get_logger
from dfetch.project.vcs import VCS
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import in_directory

logger = get_logger(__name__)


External = namedtuple(
    "External", ["name", "toplevel", "path", "revision", "url", "branch", "src"]
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

            for match in itertools.chain(
                re.finditer(r"([^\s]*)@(\d+)\s+([^\s]*)", entry),
                re.finditer(r"\.\s-\s+([^\s]+)(\s+)([^\s]+)", entry),
            ):

                url, branch, src = SvnRepo._split_url(match.group(1), repo_root)

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
                        src=src,
                    )
                ]

        return externals

    @staticmethod
    def _split_url(url: str, repo_root: str) -> Tuple[str, str, str]:

        # ../   Relative to the URL of the directory on which the svn:externals property is set
        # ^/    Relative to the root of the repository in which the svn:externals property is versioned
        # //    Relative to the scheme of the URL of the directory on which the svn:externals property is set
        # /     Relative to the root URL of the server on which the svn:externals property is versioned
        url = re.sub(r"^\^", repo_root, url)
        branch = ""
        src = ""

        for match in re.finditer(
            r"(.*)\/(branches\/[^\/]+|tags\/[^\/]+|trunk)[\/]*(.*)", url
        ):

            url = match.group(1)
            branch = match.group(2) if match.group(2) != SvnRepo.DEFAULT_BRANCH else ""
            src = match.group(3)

        return (url, branch, src)

    def check(self) -> bool:
        """Check if is SVN."""
        try:
            run_on_cmdline(logger, f"svn info {self._project.remote_url}")
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
    def list_tool_info() -> None:
        """Print out version information."""
        result = run_on_cmdline(logger, "svn --version")

        first_line = result.stdout.decode().split("\n")[0]
        tool, version = first_line.replace(",", "").split("version", maxsplit=1)
        VCS._log_tool(tool, version)

    def _check_impl(self) -> str:
        """Check if a newer version is available on the given branch."""
        info = self._get_info(self.branch)
        return info["Last Changed Rev"]

    def _fetch_impl(self) -> None:
        """Get the revision of the remote and place it at the local path."""
        rev, branch = self._determine_rev_and_branch()

        complete_path = "/".join([self.remote, branch, self._project.source]).strip("/")

        # When exporting a file, the destination directory must already exist
        pathlib.Path(os.path.dirname(self.local_path)).mkdir(
            parents=True, exist_ok=True
        )

        cmd = f"svn export --force {rev} {complete_path} {self.local_path}"

        run_on_cmdline(logger, cmd)

    def _determine_rev_and_branch(self) -> Tuple[str, str]:
        rev = ""
        branch = self.DEFAULT_BRANCH

        if self.revision and self.revision.isdigit():
            rev = f"--revision {self.revision}"

        if self.branch.startswith("tags"):
            branch = self.branch
        elif self.branch and self.branch != self.DEFAULT_BRANCH:
            branch = f"branches/{self.branch}"

        return (rev, branch)

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

    def _update_metadata(self) -> None:

        rev = self._metadata.revision
        branch = self._metadata.branch

        if not branch and not rev:
            branch = self.DEFAULT_BRANCH

        if branch and not rev:
            rev = self._get_info(branch)["Revision"]

        self._metadata.fetched(rev, branch)
