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
* **version** – scrollable list of all branches and tags (arrow keys to
  navigate, Enter to select, Esc to fall back to free-text input)
* **src** – optional sub-path; browse the remote tree with arrow keys,
  expand/collapse folders with Enter/Right/Left
* **ignore** – optional list of paths to exclude; same tree browser with
  Space to toggle multiple selections and Enter to confirm

After confirming the add you are offered to run ``dfetch update`` immediately
so the dependency is materialised without a separate command.

.. scenario-include:: ../features/add-project-through-cli.feature
"""

import argparse
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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
from dfetch.project.subproject import LsFn, SubProject
from dfetch.util.purl import vcs_url_to_purl
from dfetch.util import terminal

logger = get_logger(__name__)

# Characters that are not allowed in a project name (YAML special chars).
_UNSAFE_NAME_RE = re.compile(r"[\x00-\x1F\x7F-\x9F:#\[\]{}&*!|>'\"%@`]")


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VersionRef:
    """A resolved version reference: a branch name, tag, or commit SHA."""

    kind: Literal["branch", "tag", "revision"]
    value: str

    def apply_to(self, entry: ProjectEntryDict) -> None:
        """Write this version reference into *entry*."""
        if self.kind == "branch":
            entry["branch"] = self.value
        elif self.kind == "tag":
            entry["tag"] = self.value
        elif self.kind == "revision":
            entry["revision"] = self.value


# ---------------------------------------------------------------------------
# Command class
# ---------------------------------------------------------------------------


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
            project_entry = _non_interactive_entry(
                name=probe_entry.name,
                remote_url=remote_url,
                branch=default_branch,
                dst=guessed_dst,
                remote_to_use=remote_to_use,
            )

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

        # Offer to run update immediately (only when we already prompted the user,
        # i.e. not in --force mode where we want zero interaction).
        if not args.force and Confirm.ask(
            f"Run 'dfetch update {project_entry.name}' now?", default=True
        ):
            from dfetch.commands.update import Update  # local import avoids circular

            update_args = argparse.Namespace(
                projects=[project_entry.name],
                force=False,
                no_recommendations=False,
            )
            Update()(update_args)


# ---------------------------------------------------------------------------
# Entry construction
# ---------------------------------------------------------------------------


def _non_interactive_entry(
    *,
    name: str,
    remote_url: str,
    branch: str,
    dst: str,
    remote_to_use: Remote | None,
) -> ProjectEntry:
    """Build a ``ProjectEntry`` using inferred defaults (no user interaction)."""
    entry = ProjectEntry(
        ProjectEntryDict(name=name, url=remote_url, branch=branch, dst=dst)
    )
    if remote_to_use:
        entry.set_remote(remote_to_use)
    return entry


def _build_entry(
    *,
    name: str,
    remote_url: str,
    dst: str,
    version: VersionRef,
    src: str,
    ignore: list[str],
    remote_to_use: Remote | None,
) -> ProjectEntry:
    """Assemble a ``ProjectEntry`` from the fields collected by the wizard."""
    entry_dict: ProjectEntryDict = ProjectEntryDict(
        name=name,
        url=remote_url,
        dst=dst,
    )
    version.apply_to(entry_dict)
    if src:
        entry_dict["src"] = src
    if ignore:
        entry_dict["ignore"] = ignore
    entry = ProjectEntry(entry_dict)
    if remote_to_use:
        entry.set_remote(remote_to_use)
    return entry


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
) -> ProjectEntry:
    """Guide the user through every manifest field and return a ``ProjectEntry``."""
    logger.info("[bold blue]--- Interactive add wizard ---[/bold blue]")

    name = _ask_name(default_name, existing_projects)
    dst = _ask_dst(name, default_dst)
    version = _ask_version(
        default_branch,
        subproject.list_of_branches(),
        subproject.list_of_tags(),
    )
    with subproject.browse_tree() as ls_fn:
        src = _ask_src(ls_fn)
        ignore = _ask_ignore(ls_fn)

    return _build_entry(
        name=name,
        remote_url=remote_url,
        dst=dst,
        version=version,
        src=src,
        ignore=ignore,
        remote_to_use=remote_to_use,
    )


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
        if any(part == ".." for part in Path(dst).parts):
            logger.warning(
                f"Destination '{dst}' contains '..'. "
                "Paths must stay within the manifest directory."
            )
            continue
        return dst


def _ask_version(
    default_branch: str,
    branches: list[str],
    tags: list[str],
) -> VersionRef:
    """Choose a version (branch / tag / SHA) and return it as a ``VersionRef``.

    In a TTY shows a scrollable pick list (all branches then all tags).
    Outside a TTY (CI, pipe, tests) falls back to a numbered text menu.
    """
    ordered_branches = _prioritise_default(branches, default_branch)
    ordered_tags = _sort_tags_newest_first(tags)

    choices: list[VersionRef] = [
        *[VersionRef("branch", b) for b in ordered_branches],
        *[VersionRef("tag", t) for t in ordered_tags],
    ]

    if terminal.is_tty() and choices:
        return _scrollable_version_pick(choices, default_branch)

    return _text_version_pick(choices, default_branch, branches, tags)


def _ask_src(ls_fn: LsFn) -> str:
    """Optionally prompt for a ``src:`` sub-path or glob pattern.

    In a TTY opens a tree browser for single-path selection.
    Outside a TTY falls back to a free-text prompt.
    """
    if terminal.is_tty():
        return _tree_single_pick(ls_fn, "Source path  (Enter to select, Esc to skip)")

    return Prompt.ask(
        "  [bold]Source path[/bold]  (sub-path/glob, or Enter to fetch whole repo)",
        default="",
    ).strip()


def _ask_ignore(ls_fn: LsFn) -> list[str]:
    """Optionally prompt for ``ignore:`` paths.

    In a TTY opens a tree browser with multi-select (Space to toggle,
    Enter to confirm).  Outside a TTY falls back to a comma-separated
    free-text prompt.
    """
    if terminal.is_tty():
        return _tree_multi_pick(
            ls_fn,
            "Ignore paths  (Space to select, Enter to confirm, Esc to skip)",
        )

    raw = Prompt.ask(
        "  [bold]Ignore paths[/bold]  (comma-separated, or Enter to skip)",
        default="",
    ).strip()
    return [p.strip() for p in raw.split(",") if p.strip()] if raw else []


# ---------------------------------------------------------------------------
# Version pickers
# ---------------------------------------------------------------------------


def _scrollable_version_pick(
    choices: list[VersionRef],
    default_branch: str,
) -> VersionRef:  # pragma: no cover – interactive TTY only
    """Scrollable version picker; falls back to free-text prompt on Esc."""
    default_idx = 0
    display: list[str] = []
    for i, ref in enumerate(choices):
        if ref.kind == "branch":
            suffix = (
                f"  {terminal.DIM}(default){terminal.RESET}"
                if ref.value == default_branch
                else ""
            )
            display.append(
                f"{terminal.CYAN}{ref.value}{terminal.RESET}"
                f"  {terminal.DIM}branch{terminal.RESET}{suffix}"
            )
            if ref.value == default_branch and default_idx == 0:
                default_idx = i
        else:
            display.append(
                f"{terminal.MAGENTA}{ref.value}{terminal.RESET}"
                f"  {terminal.DIM}tag{terminal.RESET}"
            )

    selected = terminal.scrollable_pick("Version", display, default_idx=default_idx)
    if selected is not None:
        return choices[selected]

    # Esc pressed — fall back to free-text
    branches = [c.value for c in choices if c.kind == "branch"]
    tags = [c.value for c in choices if c.kind == "tag"]
    return _text_version_pick(choices, default_branch, branches, tags)


def _text_version_pick(
    choices: list[VersionRef],
    default_branch: str,
    branches: list[str],
    tags: list[str],
) -> VersionRef:
    """Numbered text-based version picker (non-TTY fallback)."""
    _print_version_menu(choices, default_branch)

    while True:
        raw = Prompt.ask(
            "  [bold]Version[/bold]  (number, branch, tag, or SHA)",
            default=default_branch,
        ).strip()

        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
            logger.warning(f"  Pick a number between 1 and {len(choices)}.")
            continue

        if raw in branches:
            return VersionRef("branch", raw)
        if raw in tags:
            return VersionRef("tag", raw)
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", raw):
            return VersionRef("revision", raw)
        if raw:
            return VersionRef("branch", raw)

        logger.warning("  Please enter a number or a version value.")


def _print_version_menu(choices: list[VersionRef], default_branch: str) -> None:
    """Render the numbered branch/tag pick list (text fallback)."""
    if not choices:
        return

    lines: list[str] = []
    for i, ref in enumerate(choices, start=1):
        marker = (
            " (default)" if ref.value == default_branch and ref.kind == "branch" else ""
        )
        colour = "cyan" if ref.kind == "branch" else "magenta"
        lines.append(
            f"  [bold white]{i:>2}[/bold white]"
            f"  [{colour}]{ref.value}[/{colour}]{marker}"
            f"  [dim]{ref.kind}[/dim]"
        )

    logger.info("\n".join(lines))


# ---------------------------------------------------------------------------
# Tree browser
# ---------------------------------------------------------------------------


@dataclass
class _TreeNode:
    """One entry in the flattened view of a remote VCS tree."""

    name: str
    path: str  # path relative to repo root
    is_dir: bool
    depth: int = 0
    expanded: bool = False
    selected: bool = False
    children_loaded: bool = False


def _expand_node(nodes: list[_TreeNode], idx: int, ls_fn: LsFn) -> None:
    """Expand the directory node at *idx*, loading children if not yet done."""
    node = nodes[idx]
    if not node.children_loaded:
        children = [
            _TreeNode(
                name=name,
                path=f"{node.path}/{name}",
                is_dir=is_dir,
                depth=node.depth + 1,
            )
            for name, is_dir in ls_fn(node.path)
        ]
        nodes[idx + 1 : idx + 1] = children
        node.children_loaded = True
    node.expanded = True


def _collapse_node(nodes: list[_TreeNode], idx: int) -> None:
    """Collapse the directory node at *idx* and remove all descendant nodes."""
    parent_depth = nodes[idx].depth
    end = idx + 1
    while end < len(nodes) and nodes[end].depth > parent_depth:
        end += 1
    del nodes[idx + 1 : end]
    nodes[idx].expanded = False


def _render_tree_lines(
    nodes: list[_TreeNode], idx: int, top: int, *, hint: str
) -> list[str]:
    """Build the list of display strings for one frame of the tree browser."""
    n = len(nodes)
    lines: list[str] = []
    for i in range(top, min(top + terminal.VIEWPORT, n)):
        node = nodes[i]
        indent = "  " * node.depth
        icon = ("▼ " if node.expanded else "▶ ") if node.is_dir else "  "
        highlight = terminal.REVERSE if i == idx else ""
        check = f"{terminal.GREEN}✓{terminal.RESET} " if node.selected else "  "
        lines.append(f"  {highlight}{indent}{check}{icon}{node.name}{terminal.RESET}")
    return lines


def _run_tree_browser(
    ls_fn: LsFn,
    title: str,
    *,
    multi: bool,
) -> list[str]:  # pragma: no cover – interactive TTY only
    """Core tree browser loop.

    Returns a list of selected paths.  In single-select mode the list has
    at most one item; in multi-select mode it may have any number.
    """
    root_entries = ls_fn("")
    if not root_entries:
        return []

    nodes: list[_TreeNode] = [
        _TreeNode(name=name, path=name, is_dir=is_dir, depth=0)
        for name, is_dir in root_entries
    ]

    hint = (
        "↑/↓ navigate  Space select  Enter confirm  →/← expand/collapse  Esc skip"
        if multi
        else "↑/↓ navigate  Enter/Space select  →/← expand/collapse  Esc skip"
    )

    screen = terminal.Screen()
    idx = 0
    top = 0

    while True:
        n = len(nodes)
        if n == 0:
            screen.clear()
            return []

        idx = max(0, min(idx, n - 1))
        if idx < top:
            top = idx
        elif idx >= top + terminal.VIEWPORT:
            top = idx - terminal.VIEWPORT + 1

        header = [f"  {terminal.BOLD}{title}{terminal.RESET}"]
        body = _render_tree_lines(nodes, idx, top, hint=hint)
        scroll_hints = []
        if top > 0:
            scroll_hints.append(f"    {terminal.DIM}↑ {top} more above{terminal.RESET}")
        remaining = n - (top + terminal.VIEWPORT)
        if remaining > 0:
            scroll_hints.append(
                f"    {terminal.DIM}↓ {remaining} more below{terminal.RESET}"
            )
        footer = [f"  {terminal.DIM}{hint}{terminal.RESET}"]

        screen.draw(header + body + scroll_hints + footer)
        key = terminal.read_key()
        node = nodes[idx]

        if key == "UP":
            idx -= 1
        elif key == "DOWN":
            idx += 1
        elif key == "PGUP":
            idx = max(0, idx - terminal.VIEWPORT)
        elif key == "PGDN":
            idx = min(n - 1, idx + terminal.VIEWPORT)
        elif key == "RIGHT":
            if node.is_dir and not node.expanded:
                _expand_node(nodes, idx, ls_fn)
        elif key == "LEFT":
            if node.is_dir and node.expanded:
                _collapse_node(nodes, idx)
            elif node.depth > 0:
                for i in range(idx - 1, -1, -1):
                    if nodes[i].depth < node.depth:
                        idx = i
                        break
        elif key == "SPACE":
            if multi:
                node.selected = not node.selected
            elif not node.is_dir:
                screen.clear()
                return [node.path]
        elif key == "ENTER":
            if multi:
                screen.clear()
                return [nd.path for nd in nodes if nd.selected]
            elif node.is_dir:
                if node.expanded:
                    _collapse_node(nodes, idx)
                else:
                    _expand_node(nodes, idx, ls_fn)
            else:
                screen.clear()
                return [node.path]
        elif key == "ESC":
            screen.clear()
            return []


def _tree_single_pick(ls_fn: LsFn, title: str) -> str:
    """Browse the remote tree and return a single selected path.

    Returns ``""`` if the user skips (Esc) or no tree is available.
    """
    result = _run_tree_browser(ls_fn, title, multi=False)
    return result[0] if result else ""


def _tree_multi_pick(ls_fn: LsFn, title: str) -> list[str]:
    """Browse the remote tree and return all selected paths.

    Returns ``[]`` if the user skips (Esc) or nothing is selected.
    """
    return _run_tree_browser(ls_fn, title, multi=True)


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
    """Sort *tags* newest-semver-first; non-semver tags appended as-is."""

    def _semver_key(tag: str) -> semver.Version | None:
        try:
            return semver.Version.parse(tag.lstrip("vV"))
        except ValueError:
            return None

    semver_tags = sorted(
        (t for t in tags if _semver_key(t) is not None),
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
    if not common_path or common_path == os.path.sep:
        return ""

    if len(destinations) == 1:
        parent = str(Path(common_path).parent)
        if parent and parent != ".":
            return (Path(parent) / project_name).as_posix()
        return ""

    return (Path(common_path) / project_name).as_posix()


def _determine_remote(remotes: Sequence[Remote], remote_url: str) -> Remote | None:
    """Return the first remote whose base URL is a prefix of *remote_url*."""
    for remote in remotes:
        if remote_url.startswith(remote.url):
            return remote
    return None
