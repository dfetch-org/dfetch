"""Svn repository."""

import contextlib
import functools
import os
import pathlib
import re
from collections.abc import Callable, Generator, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import NamedTuple
from urllib.parse import urlparse

from dfetch.log import get_logger
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import in_directory
from dfetch.vcs.patch import Patch, PatchType

logger = get_logger(__name__)

_SSH_HOST_KEY_MSGS = ("host key verification failed", "authenticity of host")


class SshHostKeyError(RuntimeError):
    """Raised when SVN cannot connect due to an untrusted SSH host key."""


# As a cli tool, we can safely assume this remains stable during the runtime, caching for speed is better
@functools.lru_cache
def _extend_env_for_non_interactive_mode() -> Mapping[str, str]:
    """Extend the environment vars for svn running in non-interactive mode."""
    env = os.environ.copy()
    ssh_cmd = env.get("SVN_SSH", "ssh")
    if "BatchMode=" not in ssh_cmd:
        ssh_cmd += " -o BatchMode=yes"
    else:
        logger.debug('BatchMode already configured in SVN_SSH: "%s"', ssh_cmd)
    env["SVN_SSH"] = ssh_cmd
    return MappingProxyType(env)


def _raise_if_ssh_host_key_error(url: str, exc: SubprocessCommandError) -> None:
    """Raise a helpful SshHostKeyError if *exc* looks like an SSH host-key failure."""
    stderr_lower = exc.stderr.lower()
    if not any(msg in stderr_lower for msg in _SSH_HOST_KEY_MSGS):
        return
    parsed = urlparse(url)
    if parsed.hostname:
        host = parsed.hostname
        target = f"{parsed.username}@{host}" if parsed.username else host
        raise SshHostKeyError(
            f"SSH host key verification failed while connecting to '{url}'.\n"
            "Add the host to your known hosts file, for example by running:\n"
            f"  ssh-keyscan {host} >> ~/.ssh/known_hosts\n"
            "Or test the SSH connection manually:\n"
            f"  ssh -T {target}"
        ) from exc
    raise SshHostKeyError(
        "SSH host key verification failed while connecting to the repository.\n"
        "Add the repository's host to your known hosts file, for example by running:\n"
        "  ssh-keyscan <host> >> ~/.ssh/known_hosts"
    ) from exc


def _run_svn_raw(args: list[str], *, url: str = "") -> bytes:
    """Run an svn subcommand and return raw stdout bytes.

    Uses --non-interactive and the non-interactive SSH env on every call.
    SSH host-key failures are converted to SshHostKeyError so callers don't
    need to handle that case individually.
    """
    try:
        result = run_on_cmdline(
            logger,
            ["svn", "--non-interactive"] + args,
            env=_extend_env_for_non_interactive_mode(),
        )
        return bytes(result.stdout)
    except SubprocessCommandError as exc:
        _raise_if_ssh_host_key_error(url, exc)
        raise


def _run_svn(args: list[str], *, url: str = "") -> str:
    """Run an svn subcommand and return decoded stdout (see _run_svn_raw)."""
    return _run_svn_raw(args, url=url).decode()


def get_svn_version() -> tuple[str, str]:
    """Get the name and version of svn."""
    first_line = _run_svn(["--version"]).split("\n", maxsplit=1)[0]
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
            _run_svn(["info", self._remote], url=self._remote)
            return True
        except SshHostKeyError:
            raise
        except SubprocessCommandError as exc:
            if exc.stderr.startswith("svn: E170013"):
                raise RuntimeError(
                    f">>>{exc.cmd}<<< failed!\n"
                    + f"'{self._remote}' is not a valid URL or unreachable:\n{exc.stdout or exc.stderr}"
                ) from exc
            return False
        except RuntimeError:
            return False

    def list_of_branches(self) -> list[str]:
        """List branch names from the ``branches/`` directory."""
        try:
            output = _run_svn(["ls", f"{self._remote}/branches"], url=self._remote)
            return [
                line.strip("/\r") for line in output.splitlines() if line.strip("/\r")
            ]
        except SshHostKeyError:
            raise
        except (SubprocessCommandError, RuntimeError):
            return []

    def list_of_tags(self) -> list[str]:
        """Get list of all available tags."""
        output = _run_svn(["ls", f"{self._remote}/tags"], url=self._remote)
        return [str(tag).strip("/\r") for tag in output.split("\n") if tag]

    @contextlib.contextmanager
    def browse_tree(
        self, version: str = ""
    ) -> Generator[Callable[[str], list[tuple[str, bool]]], None, None]:
        """Yield a callable that lists SVN tree contents for *version*.

        Resolves *version* to the correct remote path (trunk,
        ``branches/<version>``, or ``tags/<version>``), then delegates
        directory listing to ``svn ls``.  The callable returns ``(name, is_dir)`` pairs.
        """
        version = version or SvnRepo.DEFAULT_BRANCH
        if version == SvnRepo.DEFAULT_BRANCH:
            base_url = f"{self._remote}/{SvnRepo.DEFAULT_BRANCH}"
        else:
            branches_url = f"{self._remote}/branches/{version}"
            try:
                SvnRepo.get_info_from_target(branches_url)
                base_url = branches_url
            except SshHostKeyError:
                raise
            except RuntimeError:
                base_url = f"{self._remote}/tags/{version}"

        def ls(path: str = "") -> list[tuple[str, bool]]:
            url = f"{base_url}/{path}" if path else base_url
            return self.ls_tree(url)

        yield ls

    def ls_tree(self, url_path: str) -> list[tuple[str, bool]]:
        """List immediate children of *url_path* as ``(name, is_dir)`` pairs."""
        try:
            output = _run_svn(["ls", url_path], url=url_path)
            entries: list[tuple[str, bool]] = []
            for line in output.splitlines():
                line = line.strip("\r")
                if not line:
                    continue
                is_dir = line.endswith("/")
                entries.append((line.rstrip("/"), is_dir))
            return entries
        except SshHostKeyError:
            raise
        except (SubprocessCommandError, RuntimeError):
            return []


class SvnRepo:
    """An svn repository."""

    DEFAULT_BRANCH = "trunk"

    def __init__(
        self,
        path: str | pathlib.Path = ".",
    ) -> None:
        """Create a svn repo."""
        self._path = str(path)

    def is_svn(self) -> bool:
        """Check if is SVN."""
        try:
            with in_directory(self._path):
                _run_svn(["info"])
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    def externals(self) -> list[External]:
        """Get list of externals."""
        with in_directory(self._path):
            output = _run_svn(["propget", "svn:externals", "-R"])
            repo_root = SvnRepo.get_info_from_target()["Repository Root"]
            return SvnRepo._parse_externals(output, repo_root, toplevel=self._path)

    @staticmethod
    def externals_from_url(url: str, revision: str = "") -> list[External]:
        """Get list of externals from a remote SVN URL."""
        extra = ["--revision", revision] if revision else []
        output = _run_svn(["propget", "svn:externals", "-R"] + extra + [url], url=url)
        repo_root = SvnRepo.get_info_from_target(url)["Repository Root"]
        normalized = SvnRepo._normalize_url_prefix(output, url)
        return SvnRepo._parse_externals(normalized, repo_root)

    @staticmethod
    def _normalize_url_prefix(output: str, base_url: str) -> str:
        """Convert URL-mode ``svn propget -R`` output to relative-path format.

        When querying a remote URL, each entry is prefixed with the full SVN URL
        of the directory that owns the property instead of a relative path.
        Strip the base_url so the standard parser receives familiar relative paths.
        """
        base = base_url.rstrip("/")
        entries = []
        for entry in output.split(os.linesep * 2):
            if entry.startswith(base + "/"):
                after = entry[len(base) + 1 :]
                sep = after.find(" -")
                if sep >= 0:
                    rel = after[:sep] or "."
                    entry = rel + after[sep:]
            elif entry.startswith(base + " -"):
                entry = "." + entry[len(base) :]
            entries.append(entry)
        return (os.linesep * 2).join(entries)

    @staticmethod
    def _parse_externals(
        output: str, repo_root: str, toplevel: str = ""
    ) -> list[External]:
        """Parse svn propget svn:externals output into External objects.

        Args:
            output: Raw stdout from ``svn propget svn:externals -R``.
            repo_root: Repository root URL (used to resolve ``^/`` relative URLs).
            toplevel: Local working-copy root to record in each External.
        """
        externals: list[External] = []
        path_pattern = r"(.+?)\s+-"
        for entry in output.split(os.linesep * 2):
            match: re.Match[str] | None = None
            local_path: str = ""
            for match in re.finditer(path_pattern, entry):
                pass
            if match:
                local_path = match.group(1)
                entry = re.sub(path_pattern, "", entry)

            for match in re.finditer(
                r"-r\s+(\d+)\s+(\S+?)(?:@\d+)?\s+(\S+)|([^@\s-][^@\s]*)(?:@(\d+))?\s+([^\s]+)",
                entry,
            ):
                if match.group(1):
                    rev = match.group(1)
                    url = match.group(2)
                    name = match.group(3)
                else:
                    url = match.group(4)
                    rev = match.group(5) or ""
                    name = match.group(6)

                url, branch, tag, src = SvnRepo._split_url(url, repo_root)

                raw_path = "/".join(os.path.join(local_path, name).split(os.sep))
                externals += [
                    External(
                        name=name,
                        toplevel=toplevel,
                        path=raw_path[2:] if raw_path.startswith("./") else raw_path,
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
            output = _run_svn(["info", target.strip()], url=target)
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
                for line in output.split(os.linesep)
                if line and ":" in line
            )
        }

    @staticmethod
    def get_last_changed_revision(target: str | Path) -> str:
        """Get the last changed revision of the given target."""
        target_str = str(target).strip()
        if os.path.isdir(target_str):
            last_digits = re.compile(r"(?P<digits>\d+)(?!.*\d)")
            version = run_on_cmdline(logger, ["svnversion", target_str]).stdout.decode()

            parsed_version = last_digits.search(version)
            if parsed_version:
                return parsed_version.group("digits")
            raise RuntimeError(f"svnversion output was unexpected: {version}")

        return _run_svn(
            ["info", "--show-item", "last-changed-revision", target_str],
            url=target_str,
        ).strip()

    @staticmethod
    def untracked_files(path: str, ignore: Sequence[str]) -> list[str]:
        """Get list of untracked files in the working copy."""
        files = []
        for line in _run_svn(["status", path]).splitlines():
            if line.startswith("?"):
                file_path = line[1:].strip()
                if not any(
                    pathlib.Path(file_path).match(pattern) for pattern in ignore
                ):
                    files.append(file_path)
        return files

    @staticmethod
    def export(url: str, rev: str = "", dst: str = ".") -> None:
        """Export the given revision from url to destination.

        Args:
            url: Repository URL to export from.
            rev: Bare revision number (digits only) or empty string for HEAD.
                Must not include flag names such as ``--revision``.
            dst: Local destination path.

        Raises:
            ValueError: If *rev* is non-empty and contains non-digit characters.
        """
        if rev and not rev.isdigit():
            raise ValueError(f"SVN revision must be digits only, got: {rev!r}")
        _run_svn(
            ["export", "--force"] + (["--revision", rev] if rev else []) + [url, dst],
            url=url,
        )

    @staticmethod
    def files_in_path(url_path: str) -> list[str]:
        """List all files in path at the given url."""
        return _run_svn(["list", url_path], url=url_path).splitlines()

    @staticmethod
    def ignored_files(path: str) -> Sequence[str]:
        """Get list of ignored files in the working copy."""
        if not pathlib.Path(path).exists():
            return []

        with in_directory(path):
            lines = _run_svn(["status", "--no-ignore", "."]).splitlines()

        return [line[1:].strip() for line in lines if line.startswith("I")]

    @staticmethod
    def any_changes_or_untracked(path: str) -> bool:
        """List of any changed files."""
        if not pathlib.Path(path).exists():
            raise RuntimeError("Path does not exist.")

        with in_directory(path):
            return bool(_run_svn(["status", "."]).splitlines())

    def create_diff(
        self,
        old_revision: str,
        new_revision: str | None,
        ignore: Sequence[str],
    ) -> Patch:
        """Generate a relative diff patch."""
        cmd = ["diff", "--ignore-properties", "."]

        if old_revision:
            cmd.extend(
                [
                    "-r",
                    f"{old_revision}:{new_revision}" if new_revision else old_revision,
                ]
            )

        with in_directory(self._path):
            patch_text = _run_svn_raw(cmd)

        if not patch_text.strip():
            return Patch.empty().convert_type(PatchType.SVN)
        return Patch.from_bytes(patch_text).filter(ignore)

    def get_username(self) -> str:
        """Get the username of the local svn repo."""
        try:
            return _run_svn(["info", "--show-item", "author", self._path]).strip()
        except SubprocessCommandError:
            return ""
