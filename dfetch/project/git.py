"""
Git specific implementation
"""

import os

from dfetch.util.cmdline import Cmdline
from dfetch.project.vcs import VCS
from dfetch.util.util import safe_rmtree, in_directory


class GitRepo(VCS):
    """A git repository"""

    METADATA_DIR = ".git"
    DEFAULT_BRANCH = "master"

    def check(self) -> bool:
        """ Check if is GIT """
        return self._project.remote_url.endswith(".git")

    def _fetch_impl(self) -> None:
        """ Get the revision of the remote and place it at the local path """

        # also allow for revision
        branch = self.branch or self.DEFAULT_BRANCH
        cmd = f"git clone --branch {branch} --depth 1 {self.remote} {self.local_path}"

        Cmdline.run(self.logger, cmd)

        self._cleanup()

    def _update_metadata(self) -> None:

        result = Cmdline.run(self.logger, f"git ls-remote {self.remote}")

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

        rev = self._metadata.revision
        branch = self._metadata.branch

        if not branch and not rev:
            branch = self.DEFAULT_BRANCH

        if branch and not rev:
            for reference, sha in info.items():
                if reference in [f"refs/heads/{branch}", f"refs/tags/{branch}"]:
                    rev = sha
                    break
        elif not branch and rev:
            for reference, sha in info.items():
                if sha[:8] == rev[:8]:  # Also allow for shorter SHA's
                    branch = reference.replace("refs/heads", "").replace(
                        "refs/tags", ""
                    )
                    break

        self._metadata.fetched(rev, branch)

    def _cleanup(self) -> None:
        path = os.path.join(self.local_path, self.METADATA_DIR)
        safe_rmtree(path)

    def _checkout(self, revision: str) -> None:
        with in_directory(self.local_path):
            cmd = f"git checkout {revision}"
            Cmdline.run(self.logger, cmd)
