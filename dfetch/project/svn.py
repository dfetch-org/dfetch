"""SVN specific implementation."""

import os
import pathlib
import re
import urllib.parse
from collections.abc import Sequence
from typing import NamedTuple, Optional

from dfetch.log import get_logger
from dfetch.manifest.version import Version
from dfetch.project.vcs import VCS
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import (
    find_matching_files,
    find_non_matching_files,
    in_directory,
    safe_rm,
)
from dfetch.vcs.patch import (
    combine_patches,
    create_svn_patch_for_new_file,
    filter_patch,
)

logger = get_logger(__name__)


class External(NamedTuple):
    """Information about a svn external."""

    name: str
    toplevel: str
    path: str
    revision: str
    url: str
    branch: str
    tag: str
    src: str


class SvnRepo(VCS):
    """A svn repository."""

    DEFAULT_BRANCH = "trunk"
    NAME = "svn"

    @staticmethod
    def externals() -> list[External]:
        """Get list of externals."""
        result = run_on_cmdline(
            logger,
            [
                "svn",
                "--non-interactive",
                "propget",
                "svn:externals",
                "-R",
            ],
        )

        repo_root = SvnRepo._get_info_from_target()["Repository Root"]

        externals: list[External] = []
        path_pattern = r"([^\s^-]+)\s+-"
        for entry in result.stdout.decode().split(os.linesep * 2):
            match: Optional[re.Match[str]] = None
            local_path: str = ""
            for match in re.finditer(path_pattern, entry):
                pass
            if match:
                local_path = match.group(1)
                entry = re.sub(path_pattern, "", entry)

            for match in re.finditer(
                r"([^-\s\d][^\s]+)(?:@)(\d+)\s+([^\s]+)|([^-\s\d][^\s]+)\s+([^\s]+)",
                entry,
            ):
                url = match.group(1) or match.group(4)
                name = match.group(3) or match.group(5)
                rev = "" if not match.group(2) else match.group(2).strip()

                url, branch, tag, src = SvnRepo._split_url(url, repo_root)

                externals += [
                    External(
                        name=name,
                        toplevel=os.getcwd(),
                        path="/".join(os.path.join(local_path, name).split(os.sep)),
                        revision=rev,
                        url=url,
                        branch=branch,
                        tag=tag,
                        src=src,
                    )
                ]

        return externals

    @staticmethod
    def _split_url(url: str, repo_root: str) -> tuple[str, str, str, str]:
        # ../   Relative to the URL of the directory on which the svn:externals property is set
        # ^/    Relative to the root of the repository in which the svn:externals property is versioned
        # //    Relative to the scheme of the URL of the directory on which the svn:externals property is set
        # /     Relative to the root URL of the server on which the svn:externals property is versioned
        url = re.sub(r"^\^", repo_root, url)
        branch = " "
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

        if branch == " " and url.startswith(repo_root):
            src = url[len(f"{repo_root}/") :]
            url = repo_root

        return (url, branch, tag, src)

    def check(self) -> bool:
        """Check if is SVN."""
        try:
            run_on_cmdline(logger, ["svn", "info", self.remote, "--non-interactive"])
            return True
        except SubprocessCommandError as exc:
            if exc.stderr.startswith("svn: E170013"):
                raise RuntimeError(
                    f">>>{exc.cmd}<<< failed!\n"
                    + f"'{self.remote}' is not a valid URL or unreachable:\n{exc.stdout or exc.stderr}"
                ) from exc
            return False
        except RuntimeError:
            return False

    @staticmethod
    def check_path(path: str = ".") -> bool:
        """Check if is SVN."""
        try:
            with in_directory(path):
                run_on_cmdline(logger, ["svn", "info", "--non-interactive"])
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    @staticmethod
    def revision_is_enough() -> bool:
        """See if this VCS can uniquely distinguish branch with revision only."""
        return False

    def _latest_revision_on_branch(self, branch: str) -> str:
        """Get the latest revision on a branch."""
        if branch not in (self.DEFAULT_BRANCH, "", " "):
            branch = f"branches/{branch}"
        return self._get_revision(branch)

    def _does_revision_exist(self, revision: str) -> bool:
        """Check if the given revision exists."""
        raise NotImplementedError(
            "In SVN only a revision is NOT enough, this should not be called!"
        )

    def _list_of_tags(self) -> list[str]:
        """Get list of all available tags."""
        result = run_on_cmdline(
            logger, ["svn", "ls", "--non-interactive", f"{self.remote}/tags"]
        )
        return [
            str(tag).strip("/\r") for tag in result.stdout.decode().split("\n") if tag
        ]

    @staticmethod
    def list_tool_info() -> None:
        """Print out version information."""
        try:
            result = run_on_cmdline(logger, ["svn", "--version", "--non-interactive"])
        except RuntimeError as exc:
            logger.debug(
                f"Something went wrong trying to get the version of svn: {exc}"
            )
            VCS._log_tool("svn", "<not found in PATH>")
            return

        first_line = result.stdout.decode().split("\n")[0]
        tool, version = first_line.replace(",", "").split("version", maxsplit=1)
        VCS._log_tool(tool, version)

    def _determine_what_to_fetch(self, version: Version) -> tuple[str, str, str]:
        """Based on the given version, determine what to fetch.

        Args:
            version (Version): Version that needs to be fetched

        Raises:
            RuntimeError: Invalid revision

        Returns:
            Tuple[str, str, str]: branch, branch_path, revision
        """
        if version.tag:
            branch_path = f"tags/{version.tag}/"
            branch = ""
        elif version.branch == " ":
            branch_path = ""
            branch = " "
        else:
            branch = version.branch or self.DEFAULT_BRANCH
            branch_path = (
                f"branches/{branch}"
                if branch != self.DEFAULT_BRANCH
                else self.DEFAULT_BRANCH
            )

        branch_path = urllib.parse.quote(branch_path)

        revision = version.revision or self._get_revision(branch_path)

        if not revision.isdigit():
            raise RuntimeError(f"{revision} must be a number for SVN")

        return (branch, branch_path, revision)

    def _remove_ignored_files(self) -> None:
        """Remove any ignored files, whilst keeping license files."""
        for file_or_dir in find_matching_files(self.local_path, self.ignore):
            if not (file_or_dir.is_file() and self.is_license_file(file_or_dir.name)):
                safe_rm(file_or_dir)

    def _fetch_impl(self, version: Version) -> Version:
        """Get the revision of the remote and place it at the local path."""
        branch, branch_path, revision = self._determine_what_to_fetch(version)
        rev_arg = f"--revision {revision}" if revision else ""

        complete_path = "/".join(
            filter(None, [self.remote, branch_path.strip(), self.source])
        ).strip("/")

        # When exporting a file, the destination directory must already exist
        pathlib.Path(os.path.dirname(self.local_path)).mkdir(
            parents=True, exist_ok=True
        )

        complete_path, file_pattern = self._parse_file_pattern(complete_path)

        SvnRepo._export(complete_path, rev_arg, self.local_path)

        if file_pattern:
            for file in find_non_matching_files(self.local_path, (file_pattern,)):
                os.remove(file)
            if not os.listdir(self.local_path):
                logger.warning(
                    f"The 'src:' filter '{self.source}' didn't match any files from '{self.remote}'"
                )

        if self.source:
            root_branch_path = "/".join([self.remote, branch_path]).strip("/")

            for file in SvnRepo._license_files(root_branch_path):
                dest = (
                    self.local_path
                    if os.path.isdir(self.local_path)
                    else os.path.dirname(self.local_path)
                )
                SvnRepo._export(f"{root_branch_path}/{file}", rev_arg, dest)
                break

        if self.ignore:
            self._remove_ignored_files()

        return Version(tag=version.tag, branch=branch, revision=revision)

    @staticmethod
    def _parse_file_pattern(complete_path: str) -> tuple[str, str]:
        if complete_path.count("*") > 1:
            raise RuntimeError("Only single * supported in 'src:'!")

        glob_filter = ""
        if complete_path.count("*") == 1:
            before, after = complete_path.split("*", maxsplit=1)
            complete_path, before_star = before.rsplit("/", maxsplit=1)
            glob_filter = "*".join([before_star, after])
        return complete_path, glob_filter

    def _get_info(self, branch: str) -> dict[str, str]:
        return self._get_info_from_target(f"{self.remote}/{branch}")

    @staticmethod
    def _export(url: str, rev: str = "", dst: str = ".") -> None:
        run_on_cmdline(
            logger,
            ["svn", "export", "--non-interactive", "--force"]
            + rev.split(" ")
            + [url, dst],
        )

    @staticmethod
    def _files_in_path(url_path: str) -> list[str]:
        return [
            str(line)
            for line in run_on_cmdline(
                logger, ["svn", "list", "--non-interactive", url_path]
            )
            .stdout.decode()
            .splitlines()
        ]

    @staticmethod
    def _license_files(url_path: str) -> list[str]:
        return [
            str(license)
            for license in filter(
                SvnRepo.is_license_file, SvnRepo._files_in_path(url_path)
            )
        ]

    @staticmethod
    def _get_info_from_target(target: str = "") -> dict[str, str]:
        try:
            result = run_on_cmdline(
                logger, ["svn", "info", "--non-interactive", target.strip()]
            ).stdout.decode()
        except SubprocessCommandError as exc:
            if exc.stderr.startswith("svn: E170013"):
                raise RuntimeError(
                    f">>>{exc.cmd}<<< failed!\n"
                    + f"'{target.strip()}' is not a valid URL or unreachable:\n{exc.stderr or exc.stdout}"
                ) from exc
            raise

        return {
            key.strip(): value.strip()
            for key, value in (
                line.split(":", maxsplit=1) for line in result.split(os.linesep) if line
            )
        }

    def _get_revision(self, branch: str) -> str:
        return self._get_info(branch)["Revision"]

    @staticmethod
    def _get_last_changed_revision(target: str) -> str:
        if os.path.isdir(target):
            last_digits = re.compile(r"(?P<digits>\d+)(?!.*\d)")
            version = run_on_cmdline(
                logger, ["svnversion", target.strip()]
            ).stdout.decode()

            parsed_version = last_digits.search(version)
            if parsed_version:
                return parsed_version.group("digits")
            raise RuntimeError(f"svnversion output was unexpected: {version}")

        return str(
            run_on_cmdline(
                logger,
                [
                    "svn",
                    "info",
                    "--non-interactive",
                    "--show-item",
                    "last-changed-revision",
                    target.strip(),
                ],
            )
            .stdout.decode()
            .strip()
        )

    def metadata_revision(self) -> str:
        """Get the revision of the metadata file."""
        return self._get_last_changed_revision(self.metadata_path)

    def current_revision(self) -> str:
        """Get the current revision of the repo."""
        return self._get_last_changed_revision(self.local_path)

    def get_diff(
        self, old_revision: str, new_revision: Optional[str], ignore: Sequence[str]
    ) -> str:
        """Get the diff between two revisions."""
        cmd = [
            "svn",
            "diff",
            "--non-interactive",
            "--ignore-properties",
            ".",
            "-r",
            old_revision,
        ]
        if new_revision:
            cmd[-1] += f":{new_revision}"

        with in_directory(self.local_path):
            patch_text = run_on_cmdline(logger, cmd).stdout

        filtered = filter_patch(patch_text, ignore)

        if new_revision:
            return filtered

        patches: list[bytes] = [filtered.encode("utf-8")] if filtered else []
        with in_directory(self.local_path):
            for file_path in self._untracked_files(".", ignore):
                patch = create_svn_patch_for_new_file(file_path)
                if patch:
                    patches.append(patch.encode("utf-8"))

        return combine_patches(patches)

    def get_default_branch(self) -> str:
        """Get the default branch of this repository."""
        return self.DEFAULT_BRANCH

    @staticmethod
    def _untracked_files(path: str, ignore: Sequence[str]) -> list[str]:
        """Get list of untracked files in the working copy."""
        result = (
            run_on_cmdline(
                logger,
                ["svn", "status", "--non-interactive", path],
            )
            .stdout.decode()
            .splitlines()
        )

        files = []
        for line in result:
            if line.startswith("?"):
                file_path = line[1:].strip()
                if not any(
                    pathlib.Path(file_path).match(pattern) for pattern in ignore
                ):
                    files.append(file_path)
        return files

    @staticmethod
    def ignored_files(path: str) -> Sequence[str]:
        """Get list of ignored files in the working copy."""
        if not pathlib.Path(path).exists():
            return []

        with in_directory(path):
            result = (
                run_on_cmdline(
                    logger,
                    ["svn", "status", "--non-interactive", "--no-ignore", "."],
                )
                .stdout.decode()
                .splitlines()
            )

        return [line[1:].strip() for line in result if line.startswith("I")]
