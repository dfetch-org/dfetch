"""Git specific implementation."""

import functools
import glob
import os
import re
import tempfile
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from pathlib import Path

from dfetch.log import get_logger
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.util import (
    in_directory,
    is_license_file,
    move_directory_contents,
    safe_rm,
    strip_glob_prefix,
    unique_parent_dirs,
)
from dfetch.vcs.patch import Patch, PatchType

logger = get_logger(__name__)


@dataclass
class Submodule:
    """Information about a submodule."""

    name: str
    toplevel: str
    path: str
    sha: str
    url: str
    branch: str
    tag: str


@dataclass
class CheckoutOptions:
    """Options for checking out a specific version from a remote git repository."""

    remote: str
    version: str
    src: str | None = None
    must_keeps: list[str] | None = None
    ignore: Sequence[str] | None = None


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

    def list_of_branches(self) -> list[str]:
        """Get list of all available branches."""
        info = self._ls_remote(self._remote)

        return [
            reference.replace("refs/heads/", "")
            for reference, _ in info.items()
            if reference.startswith("refs/heads/")
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

    def fetch_for_tree_browse(self, target: str, version: str) -> None:
        """Fetch just enough objects to support ``ls_tree`` on *version*.

        Uses ``--no-checkout`` and ``--filter=blob:none`` so only tree objects
        are transferred — no file contents are downloaded.
        """
        run_on_cmdline(logger, ["git", "-C", target, "init"])
        run_on_cmdline(
            logger,
            [
                "git",
                "-C",
                target,
                "fetch",
                "--depth=1",
                "--filter=blob:none",
                self._remote,
                version,
            ],
            env=_extend_env_for_non_interactive_mode(),
        )

    @staticmethod
    def _parse_ls_tree_entry(line: str, prefix: str) -> tuple[str, bool]:
        """Parse one ``git ls-tree`` output line into a ``(name, is_dir)`` pair."""
        meta, name = line.split("\t", 1)
        base = name[len(prefix) :] if prefix and name.startswith(prefix) else name
        return base, meta.split()[1] == "tree"

    @staticmethod
    def ls_tree(local_path: str, path: str = "") -> list[tuple[str, bool]]:
        """List the contents of the HEAD tree at *path* in a local clone.

        Returns a list of ``(name, is_dir)`` pairs sorted with directories
        first (alphabetically), then files (alphabetically).
        """
        cmd = ["git", "-C", local_path, "ls-tree", "FETCH_HEAD"]
        if path:
            cmd.append(path.rstrip("/") + "/")
        try:
            result = run_on_cmdline(logger, cmd=cmd)
            prefix = (path.rstrip("/") + "/") if path else ""
            entries = [
                GitRemote._parse_ls_tree_entry(line, prefix)
                for line in result.stdout.decode().splitlines()
                if line.strip()
            ]
            dirs: list[tuple[str, bool]] = sorted((n, d) for n, d in entries if d)
            files: list[tuple[str, bool]] = sorted((n, d) for n, d in entries if not d)
            return dirs + files
        except SubprocessCommandError:
            return []

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
        safe_rm(temp_dir, within=Path(temp_dir).parent)

        return exists


class GitLocalRepo:
    """A git repository."""

    METADATA_DIR = ".git"
    GIT_MODULES_FILE = ".gitmodules"

    def __init__(self, path: str | Path = ".") -> None:
        """Create a local git repo."""
        self._path = str(path)

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

    def _configure_sparse_checkout(
        self,
        src: str | None,
        keeps: Sequence[str],
        ignore: Sequence[str] | None = None,
    ) -> None:
        run_on_cmdline(logger, ["git", "config", "core.sparsecheckout", "true"])

        with open(".git/info/sparse-checkout", "a", encoding="utf-8") as f:
            patterns = list(keeps or [])
            patterns.append(f"/{src or '*'}")

            if ignore:
                patterns += self._determine_ignore_paths(src, ignore)

            f.write("\n".join(map(str, patterns)) + "\n")

    def checkout_version(
        self,
        options: CheckoutOptions,
    ) -> tuple[str, list[Submodule]]:
        """Checkout a specific version from a given remote.

        Args:
            options: A :class:`CheckoutOptions` instance describing what to fetch.
        """
        with in_directory(self._path):
            run_on_cmdline(logger, ["git", "init"])
            run_on_cmdline(logger, ["git", "remote", "add", "origin", options.remote])
            run_on_cmdline(logger, ["git", "checkout", "-b", "dfetch-local-branch"])

            if options.src or options.ignore:
                self._configure_sparse_checkout(
                    options.src, options.must_keeps or [], options.ignore
                )

            run_on_cmdline(
                logger,
                ["git", "fetch", "--depth", "1", "origin", options.version],
                env=_extend_env_for_non_interactive_mode(),
            )
            run_on_cmdline(logger, ["git", "reset", "--hard", "FETCH_HEAD"])

            run_on_cmdline(
                logger,
                ["git", "submodule", "update", "--init", "--recursive"],
                env=_extend_env_for_non_interactive_mode(),
            )

            submodules = self.submodules()

            current_sha = (
                run_on_cmdline(logger, ["git", "rev-parse", "HEAD"])
                .stdout.decode()
                .strip()
            )

            submodules = self._apply_src_and_ignore(
                options.remote, options.src, options.ignore, submodules
            )

            return str(current_sha), submodules

    def _apply_src_and_ignore(
        self,
        remote: str,
        src: str | None,
        ignore: Sequence[str] | None,
        submodules: list[Submodule],
    ) -> list[Submodule]:
        """Apply src filter and ignore patterns, returning surviving submodules."""
        if src:
            for submodule in submodules:
                submodule.path = strip_glob_prefix(submodule.path, src)
            self._move_src_folder_up(remote, src)

        for ignore_path in ignore or []:
            paths = [
                p
                for p in glob.glob(ignore_path)
                if not (os.path.isfile(p) and is_license_file(os.path.basename(p)))
            ]
            safe_rm(paths, within=".")

        return [s for s in submodules if os.path.exists(s.path)]

    @staticmethod
    def _move_src_folder_up(remote: str, src: str) -> None:
        """Move the files from the src folder into the root of the project.

        Args:
            remote (str): Name of the root
            src (str): Src folder to move up
        """
        if os.path.isabs(src):
            logger.warning(
                f"The 'src:' filter '{src}' is an absolute path; skipping for '{remote}'"
            )
            return

        repo_root = Path(os.getcwd()).resolve()
        safe_matched: list[str] = []
        for p in sorted(glob.glob(src)):
            if Path(p).resolve().is_relative_to(repo_root):
                safe_matched.append(p)
            else:
                logger.warning(
                    f"The 'src:' filter '{src}' matched '{p}' outside the repo root; skipping"
                )

        if not safe_matched:
            logger.warning(
                f"The 'src:' filter '{src}' didn't match any files from '{remote}'"
            )
            return

        # Resolve to canonical absolute paths so downstream steps use stable paths
        # regardless of any '..' components in the original glob results.
        resolved_dirs = [Path(d).resolve() for d in unique_parent_dirs(safe_matched)]

        if len(resolved_dirs) > 1:
            display = resolved_dirs[0].relative_to(repo_root)
            logger.warning(
                f"The 'src:' filter '{src}' matches multiple directories from '{remote}'. "
                f"Only considering files in '{display}'."
            )

        if resolved_dirs:
            chosen = resolved_dirs[0]
            try:
                move_directory_contents(str(chosen), ".")
                parts = chosen.relative_to(repo_root).parts
                if parts:
                    safe_rm(repo_root / parts[0], within=repo_root)
            except FileNotFoundError:
                logger.warning(
                    f"The 'src:' filter '{chosen}' didn't match any files from '{remote}'"
                )

    @staticmethod
    def _determine_ignore_paths(
        src: str | None, ignore: Sequence[str]
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

    @staticmethod
    def _build_hash_args(old_hash: str | None, new_hash: str | None) -> list[str]:
        """Return the SHA positional arguments for git diff (zero, one, or two hashes)."""
        if not old_hash:
            return []
        return [old_hash, new_hash] if new_hash else [old_hash]

    @staticmethod
    def _build_ignore_args(ignore: Sequence[str] | None) -> list[str]:
        """Return git-diff pathspec arguments that exclude each pattern in *ignore*."""
        if not ignore:
            return []
        return ["--", "."] + [f":(exclude){p}" for p in ignore]

    def create_diff(
        self,
        old_hash: str | None,
        new_hash: str | None,
        ignore: Sequence[str] | None = None,
        reverse: bool = False,
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

            if reverse:
                cmd.extend(["-R", "--src-prefix=b/", "--dst-prefix=a/"])

            cmd.extend(GitLocalRepo._build_hash_args(old_hash, new_hash))
            cmd.extend(GitLocalRepo._build_ignore_args(ignore))

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

    @staticmethod
    def any_changes_or_untracked(path: str) -> bool:
        """Return True if the repo at *path* has any changed or untracked files."""
        if not Path(path).exists():
            raise RuntimeError("Path does not exist.")

        with in_directory(path):
            return bool(
                run_on_cmdline(
                    logger,
                    [
                        "git",
                        "status",
                        "--porcelain",
                        "--",
                        ".",
                    ],
                )
                .stdout.decode()
                .splitlines()
            )

    def untracked_files_patch(self, ignore: Sequence[str] | None = None) -> Patch:
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
                return Patch.for_new_files(untracked_files, PatchType.GIT)

            return Patch.empty()

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
                'printf "%s\\0%s\\0%s\\0%s\n" "$name" "$sm_path" "$sha1" "$toplevel"',
            ],
        )

        submodules: list[Submodule] = []
        urls: dict[str, str] = {}
        for line in result.stdout.decode().split("\n"):
            if line:
                name, sm_path, sha, toplevel = line.split("\0")
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

    def _get_git_config_value(self, key: str) -> str:
        """Read a single git config value from the local repo.

        Args:
            key: The git config key to query (e.g. ``user.name``).

        Returns:
            The stripped config value, or an empty string if the key is absent.
        """
        try:
            with in_directory(self._path):
                result = run_on_cmdline(logger, ["git", "config", key])
            return str(result.stdout.decode().strip())
        except SubprocessCommandError:
            return ""

    def get_username(self) -> str:
        """Get the username of the local git repo."""
        return self._get_git_config_value("user.name")

    def get_useremail(self) -> str:
        """Get the user email of the local git repo."""
        return self._get_git_config_value("user.email")
