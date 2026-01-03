"""Git specific implementation."""

import functools
import os
import re
import shutil
import tempfile
from collections.abc import Generator, Sequence
from pathlib import Path, PurePath
from typing import NamedTuple, Optional

from dfetch.log import get_logger
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import in_directory, safe_rmtree
from dfetch.vcs.patch import create_git_patch_for_new_file

logger = get_logger(__name__)


class Submodule(NamedTuple):
    """Information about a submodule."""

    name: str
    toplevel: str
    path: str
    sha: str
    url: str
    branch: str
    tag: str


def get_git_version() -> tuple[str, str]:
    """Get the name and version of git."""
    result = run_on_cmdline(logger, ["git", "--version"])
    tool, version = result.stdout.decode().strip().split("version", maxsplit=1)
    return (str(tool), str(version))


def _build_git_ssh_command() -> str:
    """Returns a safe SSH command string for Git that enforces non-interactive mode.

    Respects existing GIT_SSH_COMMAND and git core.sshCommand.
    """
    ssh_cmd = os.environ.get("GIT_SSH_COMMAND")

    if not ssh_cmd:

        try:
            result = run_on_cmdline(
                logger,
                ["git", "config", "--get", "core.sshCommand"],
            )
            ssh_cmd = result.stdout.decode().strip()

        except SubprocessCommandError:
            ssh_cmd = None

    if not ssh_cmd:
        ssh_cmd = "ssh"

    if "BatchMode=" not in ssh_cmd:
        ssh_cmd += " -o BatchMode=yes"
    else:
        logger.debug(f'BatchMode already configured in "{ssh_cmd}"')

    return ssh_cmd


# As a cli tool, we can safely assume this remains stable during the runtime, caching for speed is better
@functools.lru_cache
def _extend_env_for_non_interactive_mode() -> dict[str, str]:
    """Extend the environment vars for git running in non-interactive mode.

    See https://serverfault.com/a/1054253 for background info
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = _build_git_ssh_command()

    # https://stackoverflow.com/questions/37182847/how-do-i-disable-git-credential-manager-for-windows#answer-45513654
    env["GCM_INTERACTIVE"] = "never"
    return env


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
            run_on_cmdline(
                logger,
                cmd=["git", "ls-remote", "--heads", self._remote],
                env=_extend_env_for_non_interactive_mode(),
            )
            return True
        except SubprocessCommandError as exc:
            if exc.returncode == 128 and "Could not resolve host" in exc.stderr:
                raise RuntimeError(
                    f">>>{exc.cmd}<<< failed!\n"
                    + f"'{self._remote}' is not a valid URL or unreachable:\n{exc.stderr or exc.stdout}"
                ) from exc
            return False
        except RuntimeError:
            return False

    def last_sha_on_branch(self, branch: str) -> str:
        """Get the last sha of a branch."""
        return self._find_sha_of_branch_or_tag(self._ls_remote(self._remote), branch)

    def find_branch_tip_or_tag_from_sha(self, sha: str) -> tuple[str, str]:
        """Find branch or tag from sha."""
        return self._find_branch_tip_or_tag_from_sha(self._ls_remote(self._remote), sha)

    def list_of_tags(self) -> list[str]:
        """Get list of all available tags."""
        info = self._ls_remote(self._remote)

        return [
            reference.replace("refs/tags/", "")
            for reference, _ in info.items()
            if reference.startswith("refs/tags/")
        ]

    def get_default_branch(self) -> str:
        """Try to get the default branch or fallback to master."""
        try:
            result = run_on_cmdline(
                logger,
                cmd=["git", "ls-remote", "--symref", self._remote, "HEAD"],
                env=_extend_env_for_non_interactive_mode(),
            ).stdout.decode()
        except SubprocessCommandError:
            logger.debug(
                f"Failed determining default branch of {self._remote}, falling back to 'master'"
            )
            return "master"

        for match in re.finditer(r"ref:\s+refs/heads/(.+)\s+HEAD", result):
            return str(match.group(1))

        logger.debug(
            f"Didn't find a HEAD branch in {self._remote}, falling back to 'master'"
        )
        return "master"

    @staticmethod
    def _ls_remote(remote: str) -> dict[str, str]:
        result = run_on_cmdline(
            logger,
            cmd=["git", "ls-remote", "--heads", "--tags", remote],
            env=_extend_env_for_non_interactive_mode(),
        ).stdout.decode()

        info: dict[str, str] = {}
        for line in filter(lambda x: x, result.split("\n")):
            sha, ref = (part.strip() for part in f"{line} ".split("\t", maxsplit=1))

            # Annotated tag commit (more important)
            if ref.endswith("^{}"):
                info[ref.strip("^{}")] = sha
            elif ref not in info:
                info[ref] = sha
        return info

    @staticmethod
    def _find_sha_of_branch_or_tag(info: dict[str, str], branch_or_tag: str) -> str:
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
        info: dict[str, str], rev: str
    ) -> tuple[str, str]:
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

    def check_version_exists(
        self,
        version: str,
    ) -> bool:
        """Check if a specific version exists on the remote by simulating a local checkout.

        Args:
            version (str): A target to checkout, can be branch, tag or sha

        Returns:
            exists: A bool indicating if the version is available on the remote.
        """
        temp_dir = tempfile.mkdtemp()
        exists = False
        with in_directory(temp_dir):
            run_on_cmdline(logger, ["git", "init"])
            run_on_cmdline(logger, ["git", "remote", "add", "origin", self._remote])
            run_on_cmdline(logger, ["git", "checkout", "-b", "dfetch-local-branch"])
            try:
                run_on_cmdline(
                    logger,
                    ["git", "fetch", "--dry-run", "--depth", "1", "origin", version],
                    env=_extend_env_for_non_interactive_mode(),
                )
                exists = True
            except SubprocessCommandError as exc:
                if exc.returncode != 128:
                    raise
        safe_rmtree(temp_dir)

        return exists


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
                run_on_cmdline(
                    logger,
                    ["git", "status"],
                )
            return True
        except (SubprocessCommandError, RuntimeError):
            return False

    def checkout_version(  # pylint: disable=too-many-arguments
        self,
        *,
        remote: str,
        version: str,
        src: Optional[str] = None,
        must_keeps: Optional[list[str]] = None,
        ignore: Optional[Sequence[str]] = None,
    ) -> str:
        """Checkout a specific version from a given remote.

        Args:
            remote (str): Url or path to a remote git repository
            version (str): A target to checkout, can be branch, tag or sha
            src (Optional[str]): Optional path to subdirectory or file in repo
            must_keeps (Optional[List[str]]): Optional list of glob patterns to keep
            ignore (Optional[Sequence[str]]): Optional sequence of glob patterns to ignore (relative to src)
        """
        with in_directory(self._path):
            run_on_cmdline(logger, ["git", "init"])
            run_on_cmdline(logger, ["git", "remote", "add", "origin", remote])
            run_on_cmdline(logger, ["git", "checkout", "-b", "dfetch-local-branch"])

            if src or ignore:
                run_on_cmdline(logger, ["git", "config", "core.sparsecheckout", "true"])
                with open(
                    ".git/info/sparse-checkout", "a", encoding="utf-8"
                ) as sparse_checkout_file:
                    sparse_checkout_file.write(
                        "\n".join(list((must_keeps or []) + [f"/{src or '*'}"]))
                    )

                    if ignore:
                        ignore_abs_paths = self._determine_ignore_paths(src, ignore)

                        sparse_checkout_file.write("\n")
                        sparse_checkout_file.write("\n".join(ignore_abs_paths))

            run_on_cmdline(
                logger,
                ["git", "fetch", "--depth", "1", "origin", version],
                env=_extend_env_for_non_interactive_mode(),
            )
            run_on_cmdline(logger, ["git", "reset", "--hard", "FETCH_HEAD"])

            current_sha = (
                run_on_cmdline(logger, ["git", "rev-parse", "HEAD"])
                .stdout.decode()
                .strip()
            )

            if src:
                self.move_src_folder_up(remote, src)

            return str(current_sha)

    def move_src_folder_up(self, remote: str, src: str) -> None:
        """Move the files from the src folder into the root of the project.

        Args:
            remote (str): Name of the root
            src (str): Src folder to move up
        """
        full_src = src
        if not os.path.isdir(src):
            src = os.path.dirname(src)

        if not src:
            return

        try:
            for file_to_copy in os.listdir(src):
                shutil.move(src + "/" + file_to_copy, ".")
            safe_rmtree(PurePath(src).parts[0])
        except FileNotFoundError:
            logger.warning(
                f"The 'src:' filter '{full_src}' didn't match any files from '{remote}'"
            )
        return

    @staticmethod
    def _determine_ignore_paths(
        src: Optional[str], ignore: Sequence[str]
    ) -> Generator[str, None, None]:
        """Determine the ignore patterns relative to the given src."""
        if not src:
            ignore_base = ""
        else:
            src_parts = src.split("/")
            ignore_base = src if "*" not in src_parts[-1] else "/".join(src_parts[:-1])

            ignore_base = (
                ignore_base if ignore_base.endswith("/") else f"{ignore_base}/"
            )

        return (f"!/{ignore_base}{path}" for path in ignore)

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

    @staticmethod
    def get_remote_url() -> str:
        """Get the url of the remote origin."""
        try:
            result = run_on_cmdline(logger, ["git", "remote", "get-url", "origin"])
            decoded_result = str(result.stdout.decode())
        except SubprocessCommandError:
            decoded_result = ""

        return decoded_result

    def create_diff(
        self,
        old_hash: Optional[str],
        new_hash: Optional[str],
        ignore: Optional[Sequence[str]] = None,
    ) -> str:
        """Generate a relative diff patch."""
        with in_directory(self._path):
            cmd = [
                "git",
                "diff",
                "--relative",
                "--binary",  # Add binary content
                "--no-ext-diff",  # Don't allow external diff tools
                "--no-color",
            ]
            if old_hash:
                cmd.append(old_hash)
                if new_hash:
                    cmd.append(new_hash)

            if ignore:
                cmd.extend(["--", "."])
                for ignore_path in ignore:
                    cmd.append(f":(exclude){ignore_path}")
            result = run_on_cmdline(logger, cmd)

        return str(result.stdout.decode())

    @staticmethod
    def ignored_files(path: str) -> Sequence[str]:
        """List of ignored files."""
        if not Path(path).exists():
            return []

        with in_directory(path):
            return list(
                run_on_cmdline(
                    logger,
                    [
                        "git",
                        "ls-files",
                        "--ignored",
                        "--others",
                        "--exclude-standard",
                        ".",
                    ],
                )
                .stdout.decode()
                .splitlines()
            )

    def untracked_files_patch(self, ignore: Optional[Sequence[str]] = None) -> str:
        """Create a diff for untracked files."""
        with in_directory(self._path):
            untracked_files = (
                run_on_cmdline(
                    logger, ["git", "ls-files", "--others", "--exclude-standard"]
                )
                .stdout.decode()
                .splitlines()
            )

            if ignore:
                untracked_files = [
                    file_path
                    for file_path in untracked_files
                    if not any(Path(file_path).match(pattern) for pattern in ignore)
                ]

            if untracked_files:
                return "\n".join(
                    [create_git_patch_for_new_file(file) for file in untracked_files]
                )
            return ""

    @staticmethod
    def submodules() -> list[Submodule]:
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

        submodules: list[Submodule] = []
        urls: dict[str, str] = {}
        for line in result.stdout.decode().split("\n"):
            if line:
                name, sm_path, sha, toplevel = line.split(" ")
                urls = urls or GitLocalRepo._get_submodule_urls(toplevel)
                url = urls[name]
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
    def _get_submodule_urls(toplevel: str) -> dict[str, str]:
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

        origin_url = GitLocalRepo.get_remote_url()
        return {
            str(match.group(1)): GitLocalRepo._ensure_abs_url(
                origin_url, str(match.group(2))
            )
            for match in re.finditer(
                r"submodule\.(.*)\.url\s+(.*)", result.stdout.decode()
            )
        }

    @staticmethod
    def _ensure_abs_url(root_url: str, rel_url: str) -> str:
        """Make sure the given url is an absolute url."""
        if not rel_url.startswith("../"):
            return rel_url

        new_root_url = root_url.split("/")
        new_rel_url = rel_url.split("/")
        for elt in new_rel_url.copy():
            if elt != "..":
                break

            new_root_url.pop()
            new_rel_url.pop(0)

        return "/".join(new_root_url + new_rel_url)

    def find_branch_containing_sha(self, sha: str) -> str:
        """Try to find the branch that contains the given sha."""
        if not os.path.isdir(os.path.join(self._path, GitLocalRepo.METADATA_DIR)):
            return ""

        with in_directory(self._path):
            result = run_on_cmdline(
                logger,
                ["git", "branch", "--contains", sha],
            )

        branches: list[str] = [
            branch.strip()
            for branch in result.stdout.decode().split("*")
            if branch.strip() and "HEAD detached at" not in branch.strip()
        ]

        return "" if not branches else branches[0]
