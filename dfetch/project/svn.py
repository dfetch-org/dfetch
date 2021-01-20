"""SVN specific implementation."""

import os
import logging
import pathlib

from dfetch.project.vcs import VCS
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import in_directory


class SvnRepo(VCS):
    """A svn repository."""

    DEFAULT_BRANCH = "trunk"

    def check(self) -> bool:
        """Check if is SVN."""
        try:
            run_on_cmdline(self._logger, f"svn info {self._project.remote_url}")
            return True
        except SubprocessCommandError:
            return False

    @staticmethod
    def check_path(logger: logging.Logger, path: str = ".") -> bool:
        """Check if is SVN."""
        try:
            with in_directory(path):
                run_on_cmdline(logger, "svn info")
            return True
        except SubprocessCommandError:
            return False

    @staticmethod
    def list_tool_info(logger: logging.Logger) -> None:
        """Print out version information."""
        result = run_on_cmdline(logger, "svn --version")

        first_line = result.stdout.decode().split("\n")[0]
        tool, version = first_line.replace(",", "").split("version", maxsplit=1)
        VCS._log_tool(logger, tool, version)

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

        cmd = f"svn export {rev} {complete_path} {self.local_path}"

        run_on_cmdline(self.logger, cmd)

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
        result = run_on_cmdline(self.logger, f"svn info {self.remote}/{branch}")

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
