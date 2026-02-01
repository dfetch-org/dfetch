"""Svn repository."""

import os
import pathlib
import re
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple, Optional, Union

from dfetch.log import get_logger
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import in_directory
from dfetch.vcs.patch import filter_patch

logger = get_logger(__name__)


def get_svn_version() -> tuple[str, str]:
    """Get the name and version of svn."""
    result = run_on_cmdline(logger, ["svn", "--version", "--non-interactive"])
    first_line = result.stdout.decode().split("\n")[0]
    if "version" not in first_line.lower():
        raise RuntimeError(f"Unexpected svn --version output format: {first_line}")
    tool, version = first_line.replace(",", "").split("version", maxsplit=1)
    return (str(tool), str(version))


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


class SvnRemote:
    """A remote svn repository."""

    def __init__(self, remote: str) -> None:
        """Create a svn remote repo."""
        self._remote = remote

    def is_svn(self) -> bool:
        """Check if is SVN."""
        try:
            run_on_cmdline(logger, ["svn", "info", self._remote, "--non-interactive"])
            return True
        except SubprocessCommandError as exc:
            if exc.stderr.startswith("svn: E170013"):
                raise RuntimeError(
                    f">>>{exc.cmd}<<< failed!\n"
                    + f"'{self._remote}' is not a valid URL or unreachable:\n{exc.stdout or exc.stderr}"
                ) from exc
            return False
        except RuntimeError:
            return False

    def list_of_tags(self) -> list[str]:
        """Get list of all available tags."""
        result = run_on_cmdline(
            logger, ["svn", "ls", "--non-interactive", f"{self._remote}/tags"]
        )
        return [
            str(tag).strip("/\r") for tag in result.stdout.decode().split("\n") if tag
        ]


class SvnRepo:
    """An svn repository."""

    DEFAULT_BRANCH = "trunk"

    def __init__(
        self,
        path: Union[str, pathlib.Path] = ".",
    ) -> None:
        """Create a svn repo."""
        self._path = str(path)

    def is_svn(self) -> bool:
        """Check if is SVN."""
        try:
            with in_directory(self._path):
                run_on_cmdline(logger, ["svn", "info", "--non-interactive"])
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    def externals(self) -> list[External]:
        """Get list of externals."""
        with in_directory(self._path):
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

            repo_root = SvnRepo.get_info_from_target()["Repository Root"]

            externals: list[External] = []
            # Pattern matches: "path - ..." where path is the local directory
            path_pattern = r"([^\s^-]+)\s+-"
            for entry in result.stdout.decode().split(os.linesep * 2):
                match: Optional[re.Match[str]] = None
                local_path: str = ""
                for match in re.finditer(path_pattern, entry):
                    pass
                if match:
                    local_path = match.group(1)
                    entry = re.sub(path_pattern, "", entry)

                # Pattern matches either:
                # - url@revision name (pinned)
                # - url name (unpinned)
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
                            toplevel=self._path,
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

    @staticmethod
    def get_info_from_target(target: str = "") -> dict[str, str]:
        """Get the info of the given target."""
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
                line.split(":", maxsplit=1)
                for line in result.split(os.linesep)
                if line and ":" in line
            )
        }

    @staticmethod
    def get_last_changed_revision(target: Union[str, Path]) -> str:
        """Get the last changed revision of the given target."""
        target_str = str(target).strip()
        if os.path.isdir(target_str):
            last_digits = re.compile(r"(?P<digits>\d+)(?!.*\d)")
            version = run_on_cmdline(logger, ["svnversion", target_str]).stdout.decode()

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
                    target_str,
                ],
            )
            .stdout.decode()
            .strip()
        )

    @staticmethod
    def untracked_files(path: str, ignore: Sequence[str]) -> list[str]:
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
    def export(url: str, rev: str = "", dst: str = ".") -> None:
        """Export the given revision from url to destination."""
        run_on_cmdline(
            logger,
            ["svn", "export", "--non-interactive", "--force"]
            + (rev.split(" ") if rev else [])
            + [url, dst],
        )

    @staticmethod
    def files_in_path(url_path: str) -> list[str]:
        """List all files in path at the given url."""
        return [
            str(line)
            for line in run_on_cmdline(
                logger, ["svn", "list", "--non-interactive", url_path]
            )
            .stdout.decode()
            .splitlines()
        ]

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

    @staticmethod
    def any_changes_or_untracked(path: str) -> bool:
        """List of any changed files."""
        if not pathlib.Path(path).exists():
            raise RuntimeError("Path does not exist.")

        with in_directory(path):
            return bool(
                run_on_cmdline(
                    logger,
                    [
                        "svn",
                        "status",
                        ".",
                    ],
                )
                .stdout.decode()
                .splitlines()
            )

    def create_diff(
        self,
        old_revision: str,
        new_revision: Optional[str],
        ignore: Sequence[str],
    ) -> str:
        """Generate a relative diff patch."""
        cmd = ["svn", "diff", "--non-interactive", "--ignore-properties", "."]

        if old_revision:
            cmd.extend(
                [
                    "-r",
                    f"{old_revision}:{new_revision}" if new_revision else old_revision,
                ]
            )

        with in_directory(self._path):
            patch_text = run_on_cmdline(logger, cmd).stdout

        return filter_patch(patch_text, ignore)
