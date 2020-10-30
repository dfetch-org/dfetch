"""SVN specific implementation."""

import os
from typing import Dict, Tuple

from dfetch.project.vcs import VCS
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline


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

    def _check_impl(self) -> str:
        """Check if a newer version is available on the given branch."""
        info = self._get_info(self.branch)
        return info["Revision"]

    def _fetch_impl(self) -> None:
        """Get the revision of the remote and place it at the local path."""
        rev, branch = self._determine_rev_and_branch()
        cmd = f"svn export {rev} {self.remote}/{branch} {self.local_path}"

        run_on_cmdline(self.logger, cmd)

    def _determine_rev_and_branch(self) -> Tuple[str, str]:
        rev = ""
        branch = "trunk"

        if self.revision and self.revision.isdigit():
            rev = f"--revision {self.revision}"
        if self.branch and self.branch != self.DEFAULT_BRANCH:
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
