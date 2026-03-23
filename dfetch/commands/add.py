"""*Dfetch* can add projects to the manifest through the CLI.

Sometimes you want to add a project to your manifest, but you don't want to
edit the manifest by hand. With ``dfetch add`` you can add a project to your
manifest through the command line.

Non-interactive mode
--------------------
In the simplest form you just provide the URL::

    dfetch add https://github.com/some-org/some-repo.git

Dfetch fetches remote metadata (branches, tags), picks the default branch,
guesses a destination path from your existing projects, shows a preview, and
appends the entry to ``dfetch.yaml`` after a single confirmation prompt.

Skip the confirmation with ``--force``::

    dfetch add -f https://github.com/some-org/some-repo.git

Interactive mode
----------------
Use ``--interactive`` (``-i``) for a guided, step-by-step wizard::

    dfetch add -i https://github.com/some-org/some-repo.git

The wizard walks through:

* **name** – defaults to the repository name extracted from the URL
* **dst** – local destination; defaults to a path guessed from existing projects
* **version** – pick from a short numbered list of branches and tags (most
  relevant shown first; type any other value to use it directly)
* **src** – optional sub-path or glob to fetch only part of the repo

All prompts have a pre-filled default so you can just press *Enter* to accept.
The entry is appended at the end of the manifest; run ``dfetch update``
afterwards to materialise the dependency.

.. scenario-include:: ../features/add-project-through-cli.feature
"""

import argparse
import os
import re
from collections.abc import Sequence
from pathlib import Path

import semver
from rich.prompt import Confirm, Prompt

import dfetch.commands.command
import dfetch.manifest.project
import dfetch.project
from dfetch.log import get_logger
from dfetch.manifest.manifest import append_entry_manifest_file
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote
from dfetch.project import create_sub_project, create_super_project
from dfetch.project.subproject import SubProject
from dfetch.util.purl import vcs_url_to_purl

logger = get_logger(__name__)

# Maximum number of branches/tags shown in the pick list.
_MAX_CHOICES = 5

# Characters that are not allowed in a project name or destination path.
# (YAML special chars that could break the manifest even after yaml.dump)
_UNSAFE_NAME_RE = re.compile(r"[\x00-\x1F\x7F-\x9F:#\[\]{}&*!|>'\"%@`]")


class Add(dfetch.commands.command.Command):
    """Add a new project to the manifest.

    Append a project entry to the manifest without fetching.
    Use -i/--interactive to be guided through each field.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Add)

        parser.add_argument(
            "remote_url",
            metavar="<remote_url>",
            type=str,
            nargs=1,
            help="Remote URL of the repository to add.",
        )

        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Skip the confirmation prompt.",
        )

        parser.add_argument(
            "-i",
            "--interactive",
            action="store_true",
            help=(
                "Interactively guide through each manifest field. "
                "Dfetch fetches the remote branch/tag list and lets "
                "you pick or override every value."
            ),
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the add."""
        superproject = create_super_project()

        remote_url: str = args.remote_url[0]
        purl = vcs_url_to_purl(remote_url)

        # Build a minimal entry so we can probe the remote.
        probe_entry = ProjectEntry(ProjectEntryDict(name=purl.name, url=remote_url))

        # Determines VCS type; tries to reach the remote.
        subproject = create_sub_project(probe_entry)

        _check_name_uniqueness(probe_entry.name, superproject.manifest.projects)

        remote_to_use = _determine_remote(
            superproject.manifest.remotes, probe_entry.remote_url
        )
        if remote_to_use:
            logger.debug(
                f"Remote URL {probe_entry.remote_url} matches remote {remote_to_use.name}"
            )

        guessed_dst = _guess_destination(
            probe_entry.name, superproject.manifest.projects
        )
        default_branch = subproject.get_default_branch()

        if args.interactive:
            project_entry = _interactive_flow(
                remote_url=remote_url,
                default_name=probe_entry.name,
                default_dst=guessed_dst,
                default_branch=default_branch,
                subproject=subproject,
                remote_to_use=remote_to_use,
                existing_projects=superproject.manifest.projects,
            )
        else:
            project_entry = ProjectEntry(
                ProjectEntryDict(
                    name=probe_entry.name,
                    url=remote_url,
                    branch=default_branch,
                    dst=guessed_dst,
                ),
            )
            if remote_to_use:
                project_entry.set_remote(remote_to_use)

        if project_entry is None:
            return

        logger.print_overview(
            project_entry.name,
            "Will add following entry to manifest:",
            project_entry.as_yaml(),
        )

        if not args.force and not Confirm.ask("Add project to manifest?", default=True):
            logger.print_warning_line(project_entry.name, "Aborting add of project")
            return

        append_entry_manifest_file(
            (superproject.root_directory / superproject.manifest.path).absolute(),
            project_entry,
        )

        logger.print_info_line(project_entry.name, "Added project to manifest")


# ---------------------------------------------------------------------------
# Interactive flow
# ---------------------------------------------------------------------------


def _interactive_flow(
    remote_url: str,
    default_name: str,
    default_dst: str,
    default_branch: str,
    subproject: SubProject,
    remote_to_use: Remote | None,
    existing_projects: Sequence[ProjectEntry],
) -> ProjectEntry | None:
    """Guide the user through every manifest field and return a ``ProjectEntry``.

    Returns ``None`` when the user aborts the wizard.
    """
    logger.info("[bold blue]--- Interactive add wizard ---[/bold blue]")

    # --- name ---
    name = _ask_name(default_name, existing_projects)

    # --- dst ---
    dst = _ask_dst(name, default_dst)

    # --- version (branch or tag) ---
    branches = subproject.list_of_branches()
    tags = subproject.list_of_tags()
    version_type, version_value = _ask_version(default_branch, branches, tags)

    # --- src (optional) ---
    src = _ask_src()

    entry_dict: ProjectEntryDict = ProjectEntryDict(
        name=name,
        url=remote_url,
        dst=dst,
    )

    if version_type == "branch":
        entry_dict["branch"] = version_value
    elif version_type == "tag":
        entry_dict["tag"] = version_value
    elif version_type == "revision":
        entry_dict["revision"] = version_value

    if src:
        entry_dict["src"] = src

    project_entry = ProjectEntry(entry_dict)
    if remote_to_use:
        project_entry.set_remote(remote_to_use)

    return project_entry


# ---------------------------------------------------------------------------
# Individual prompt helpers
# ---------------------------------------------------------------------------


def _ask_name(default: str, existing_projects: Sequence[ProjectEntry]) -> str:
    """Prompt for the project name, re-asking on duplicates or invalid input."""
    existing_names = {p.name for p in existing_projects}
    while True:
        name = Prompt.ask("  [bold]Name[/bold]", default=default).strip()
        if not name:
            logger.warning("Name cannot be empty.")
            continue
        if _UNSAFE_NAME_RE.search(name):
            logger.warning(
                f"Name '{name}' contains characters not allowed in a manifest name. "
                "Avoid: # : [ ] {{ }} & * ! | > ' \" % @ `"
            )
            continue
        if name in existing_names:
            logger.warning(
                f"A project named '{name}' already exists. Choose a different name."
            )
            continue
        return name


def _ask_dst(name: str, default: str) -> str:
    """Prompt for the destination path, re-asking on path-traversal attempts."""
    suggested = default or name
    while True:
        dst = Prompt.ask(
            "  [bold]Destination[/bold] (path relative to manifest)",
            default=suggested,
        ).strip()
        if not dst:
            return name  # fall back to project name
        # Block path traversal: reject any component that is '..'
        if any(part == ".." for part in Path(dst).parts):
            logger.warning(
                f"Destination '{dst}' contains '..'. Paths must stay within the manifest directory."
            )
            continue
        return dst


def _ask_version(
    default_branch: str,
    branches: list[str],
    tags: list[str],
) -> tuple[str, str]:
    """Show a short pick-list of branches and tags and let the user choose one.

    The list is limited to ``_MAX_CHOICES`` entries each for branches and
    tags.  The user can pick by number, or type any branch/tag/SHA directly.
    Returns a ``(type, value)`` tuple.
    """
    choices: list[tuple[str, str]] = []  # (type, value)

    # Branches: put the default branch first, then a few more.
    ordered_branches = _prioritise_default(branches, default_branch)[:_MAX_CHOICES]
    for b in ordered_branches:
        choices.append(("branch", b))

    # Tags: most-recent semver tags first, then the rest.
    ordered_tags = _sort_tags_newest_first(tags)[:_MAX_CHOICES]
    for t in ordered_tags:
        choices.append(("tag", t))

    _print_version_menu(choices, default_branch)

    while True:
        raw = Prompt.ask(
            "  [bold]Version[/bold]  (number, branch, tag, or SHA)",
            default=default_branch,
        ).strip()

        # Numeric pick.
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
            logger.warning(f"  Pick a number between 1 and {len(choices)}.")
            continue

        # Check if it matches a known branch or tag.
        if raw in branches:
            return ("branch", raw)
        if raw in tags:
            return ("tag", raw)

        # Assume it's a SHA revision if it looks like a hex string (≥ 7 chars).
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", raw):
            return ("revision", raw)

        # Otherwise treat as a branch name (the most common case for typing a
        # custom value the user knows but that didn't appear in the short list).
        if raw:
            return ("branch", raw)

        logger.warning("  Please enter a number or a version value.")


def _print_version_menu(choices: list[tuple[str, str]], default_branch: str) -> None:
    """Render the numbered branch/tag pick list."""
    if not choices:
        return

    lines: list[str] = []
    for i, (vtype, value) in enumerate(choices, start=1):
        marker = " (default)" if value == default_branch and vtype == "branch" else ""
        colour = "cyan" if vtype == "branch" else "magenta"
        tag_label = f"[dim]{vtype}[/dim]"
        lines.append(
            f"  [bold white]{i:>2}[/bold white]  [{colour}]{value}[/{colour}]{marker}  {tag_label}"
        )

    # Indicate if there are more options not shown.
    panel_content = "\n".join(lines)
    logger.info(panel_content)


def _ask_src() -> str:
    """Optionally prompt for a ``src:`` sub-path or glob pattern."""
    src = Prompt.ask(
        "  [bold]Source path[/bold]  (sub-path/glob, or Enter to fetch whole repo)",
        default="",
    ).strip()
    return src


# ---------------------------------------------------------------------------
# Sorting / ordering helpers
# ---------------------------------------------------------------------------


def _prioritise_default(branches: list[str], default: str) -> list[str]:
    """Return *branches* with *default* moved to position 0."""
    if default in branches:
        rest = [b for b in branches if b != default]
        return [default, *rest]
    return branches


def _sort_tags_newest_first(tags: list[str]) -> list[str]:
    """Sort *tags* with semver-parseable tags newest-first; others appended."""

    def _semver_key(tag: str) -> semver.Version | None:
        cleaned = tag.lstrip("vV")
        try:
            return semver.Version.parse(cleaned)
        except ValueError:
            return None

    semver_tags = sorted(
        [t for t in tags if _semver_key(t) is not None],
        key=lambda t: _semver_key(t),  # type: ignore[arg-type, return-value]
        reverse=True,
    )
    non_semver = [t for t in tags if _semver_key(t) is None]
    return semver_tags + non_semver


# ---------------------------------------------------------------------------
# Non-interactive helpers
# ---------------------------------------------------------------------------


def _check_name_uniqueness(
    project_name: str, manifest_projects: Sequence[ProjectEntry]
) -> None:
    """Raise if *project_name* is already used in the manifest."""
    if project_name in [project.name for project in manifest_projects]:
        raise RuntimeError(
            f"Project with name '{project_name}' already exists in manifest!"
        )


def _guess_destination(
    project_name: str, manifest_projects: Sequence[ProjectEntry]
) -> str:
    """Guess the destination based on the common prefix of existing projects.

    With two or more existing projects the common parent directory is used.
    With a single existing project its parent directory is used (if any).
    """
    destinations = [p.destination for p in manifest_projects if p.destination]
    if not destinations:
        return ""

    common_path = os.path.commonpath(destinations)

    if common_path and common_path != os.path.sep:
        # For a single project whose name *is* the destination the common_path
        # equals that destination, so we take its parent directory instead.
        if len(destinations) == 1:
            parent = str(Path(common_path).parent)
            if parent and parent != ".":
                return (Path(parent) / project_name).as_posix()
            return ""
        return (Path(common_path) / project_name).as_posix()
    return ""


def _determine_remote(remotes: Sequence[Remote], remote_url: str) -> Remote | None:
    """Return the first remote whose base URL is a prefix of *remote_url*."""
    for remote in remotes:
        if remote_url.startswith(remote.url):
            return remote
    return None
