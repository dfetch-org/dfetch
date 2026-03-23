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
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
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

# ---------------------------------------------------------------------------
# ANSI codes used in the scrollable / tree UI (plain stdout; no Rich markup)
# ---------------------------------------------------------------------------
_R = "\x1b[0m"  # reset
_B = "\x1b[1m"  # bold
_D = "\x1b[2m"  # dim
_CYN = "\x1b[36m"  # cyan  – branches
_MAG = "\x1b[35m"  # magenta – tags
_GRN = "\x1b[32m"  # green  – selected ✓
_YLW = "\x1b[33m"  # yellow – cursor ▶
_HL = "\x1b[7m"  # reverse-video – highlighted row

# Viewport height for scrollable lists.
_VIEWPORT = 10

# Characters that are not allowed in a project name (YAML special chars).
_UNSAFE_NAME_RE = re.compile(r"[\x00-\x1F\x7F-\x9F:#\[\]{}&*!|>'\"%@`]")


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

        # Offer to run update immediately (only when we prompted the user, i.e.
        # not in --force mode where we want zero interaction).
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

    # --- src and ignore (browsed from a single minimal clone) ---
    with subproject.browse_tree() as ls_fn:
        src = _ask_src(ls_fn)
        ignore = _ask_ignore(ls_fn)

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

    if ignore:
        entry_dict["ignore"] = ignore

    project_entry = ProjectEntry(entry_dict)
    if remote_to_use:
        project_entry.set_remote(remote_to_use)

    return project_entry


# ---------------------------------------------------------------------------
# Terminal UI helpers
# ---------------------------------------------------------------------------


def _is_tty() -> bool:
    """Return True when running attached to an interactive terminal."""
    return sys.stdin.isatty() and not os.environ.get("CI")


def _read_key() -> str:  # pragma: no cover – raw terminal input
    """Read one keypress from stdin in raw mode; return a normalised key name."""
    if sys.platform == "win32":
        import msvcrt  # type: ignore[import]

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            return {
                "H": "UP",
                "P": "DOWN",
                "K": "LEFT",
                "M": "RIGHT",
                "I": "PGUP",
                "Q": "PGDN",
            }.get(ch2, "UNKNOWN")
        if ch in ("\r", "\n"):
            return "ENTER"
        if ch == "\x1b":
            return "ESC"
        if ch == " ":
            return "SPACE"
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch
    else:
        import select as _select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = os.read(fd, 1)
            if ch in (b"\r", b"\n"):
                return "ENTER"
            if ch == b"\x1b":
                r, _, _ = _select.select([fd], [], [], 0.05)
                if r:
                    rest = b""
                    while True:
                        r2, _, _ = _select.select([fd], [], [], 0.01)
                        if not r2:
                            break
                        rest += os.read(fd, 1)
                    return {
                        b"\x1b[A": "UP",
                        b"\x1b[B": "DOWN",
                        b"\x1b[C": "RIGHT",
                        b"\x1b[D": "LEFT",
                        b"\x1b[5~": "PGUP",
                        b"\x1b[6~": "PGDN",
                    }.get(ch + rest, "ESC")
                return "ESC"
            if ch == b" ":
                return "SPACE"
            if ch in (b"\x03", b"\x04"):
                raise KeyboardInterrupt
            return ch.decode("utf-8", errors="replace")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


class _Screen:
    """Minimal ANSI helper for in-place redraw (writes directly to stdout)."""

    def __init__(self) -> None:
        self._lines = 0

    def draw(self, lines: list[str]) -> None:
        if self._lines:
            sys.stdout.write(f"\x1b[{self._lines}A\x1b[0J")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        self._lines = len(lines)

    def clear(self) -> None:
        if self._lines:
            sys.stdout.write(f"\x1b[{self._lines}A\x1b[0J")
            sys.stdout.flush()
            self._lines = 0


def _scrollable_pick(
    title: str,
    display_items: list[str],
    *,
    default_idx: int = 0,
) -> int | None:  # pragma: no cover – interactive TTY only
    """Scrollable single-pick list.

    *display_items* are pre-formatted strings (may include raw ANSI codes).
    Returns the selected index, or ``None`` when the user pressed Esc.
    """
    screen = _Screen()
    idx = default_idx
    top = 0
    n = len(display_items)

    while True:
        idx = max(0, min(idx, n - 1))
        if idx < top:
            top = idx
        elif idx >= top + _VIEWPORT:
            top = idx - _VIEWPORT + 1

        lines: list[str] = [f"  {_B}{title}{_R}"]
        for i in range(top, min(top + _VIEWPORT, n)):
            cursor = f"{_YLW}▶{_R}" if i == idx else " "
            hl_s = _HL if i == idx else ""
            hl_e = _R if i == idx else ""
            lines.append(f"  {cursor} {hl_s}{display_items[i]}{hl_e}")

        if top > 0:
            lines.append(f"    {_D}↑ {top} more above{_R}")
        remaining = n - (top + _VIEWPORT)
        if remaining > 0:
            lines.append(f"    {_D}↓ {remaining} more below{_R}")
        lines.append(
            f"  {_D}↑/↓ navigate  PgUp/PgDn jump  Enter select  Esc free-type{_R}"
        )

        screen.draw(lines)
        key = _read_key()

        if key == "UP":
            idx -= 1
        elif key == "DOWN":
            idx += 1
        elif key == "PGUP":
            idx = max(0, idx - _VIEWPORT)
        elif key == "PGDN":
            idx = min(n - 1, idx + _VIEWPORT)
        elif key == "ENTER":
            screen.clear()
            return idx
        elif key == "ESC":
            screen.clear()
            return None


# ---------------------------------------------------------------------------
# Tree browser
# ---------------------------------------------------------------------------


@dataclass
class _TreeNode:
    name: str
    path: str  # relative from repo root
    is_dir: bool
    depth: int = 0
    expanded: bool = False
    selected: bool = False
    children_loaded: bool = False


def _expand_node(
    nodes: list[_TreeNode],
    idx: int,
    ls_fn: Callable[[str], list[tuple[str, bool]]],
) -> None:
    """Expand the directory node at *idx*, loading children if needed."""
    node = nodes[idx]
    if not node.children_loaded:
        entries = ls_fn(node.path)
        children = [
            _TreeNode(
                name=name,
                path=f"{node.path}/{name}",
                is_dir=is_dir,
                depth=node.depth + 1,
            )
            for name, is_dir in entries
        ]
        nodes[idx + 1 : idx + 1] = children
        node.children_loaded = True
    node.expanded = True


def _collapse_node(nodes: list[_TreeNode], idx: int) -> None:
    """Collapse the directory node at *idx*, removing all descendant nodes."""
    parent_depth = nodes[idx].depth
    i = idx + 1
    while i < len(nodes) and nodes[i].depth > parent_depth:
        i += 1
    del nodes[idx + 1 : i]
    nodes[idx].expanded = False


def _tree_browser(
    ls_fn: Callable[[str], list[tuple[str, bool]]],
    title: str,
    *,
    multi: bool = False,
) -> list[str] | str | None:  # pragma: no cover – interactive TTY only
    """Interactive tree browser.

    ``multi=False`` (default) — single-select; returns the selected path
    string, ``""`` if the user skips with Esc, or ``None`` on keyboard
    interrupt.

    ``multi=True`` — multi-select; Space toggles selection, Enter confirms;
    returns a (possibly empty) ``list[str]``, or ``None`` on keyboard
    interrupt.
    """
    root_entries = ls_fn("")
    if not root_entries:
        return [] if multi else ""

    nodes: list[_TreeNode] = [
        _TreeNode(name=name, path=name, is_dir=is_dir, depth=0)
        for name, is_dir in root_entries
    ]

    screen = _Screen()
    idx = 0
    top = 0

    while True:
        n = len(nodes)
        if n == 0:
            screen.clear()
            return [] if multi else ""

        idx = max(0, min(idx, n - 1))
        if idx < top:
            top = idx
        elif idx >= top + _VIEWPORT:
            top = idx - _VIEWPORT + 1

        lines: list[str] = [f"  {_B}{title}{_R}"]
        for i in range(top, min(top + _VIEWPORT, n)):
            node = nodes[i]
            indent = "  " * node.depth
            if node.is_dir:
                arrow = "▼" if node.expanded else "▶"
                icon = f"{arrow} "
            else:
                icon = "  "
            cursor = _HL if i == idx else ""
            sel = f"{_GRN}✓{_R} " if node.selected else "  "
            lines.append(f"  {cursor}{indent}{sel}{icon}{node.name}{_R}")

        if top > 0:
            lines.append(f"    {_D}↑ {top} more above{_R}")
        remaining = n - (top + _VIEWPORT)
        if remaining > 0:
            lines.append(f"    {_D}↓ {remaining} more below{_R}")

        if multi:
            lines.append(
                f"  {_D}↑/↓ navigate  Space select  Enter confirm  →/← expand/collapse  Esc skip{_R}"
            )
        else:
            lines.append(
                f"  {_D}↑/↓ navigate  Enter/Space select  →/← expand/collapse  Esc skip{_R}"
            )

        screen.draw(lines)
        key = _read_key()
        node = nodes[idx]

        if key == "UP":
            idx -= 1
        elif key == "DOWN":
            idx += 1
        elif key == "PGUP":
            idx = max(0, idx - _VIEWPORT)
        elif key == "PGDN":
            idx = min(n - 1, idx + _VIEWPORT)
        elif key == "RIGHT":
            if node.is_dir and not node.expanded:
                _expand_node(nodes, idx, ls_fn)
        elif key == "LEFT":
            if node.is_dir and node.expanded:
                _collapse_node(nodes, idx)
            elif node.depth > 0:
                # Jump to parent node
                for i in range(idx - 1, -1, -1):
                    if nodes[i].depth < node.depth:
                        idx = i
                        break
        elif key == "SPACE":
            if multi:
                node.selected = not node.selected
            elif not node.is_dir:
                screen.clear()
                return node.path
        elif key == "ENTER":
            if multi:
                # Confirm all selected items
                selected = [nd.path for nd in nodes if nd.selected]
                screen.clear()
                return selected
            elif node.is_dir:
                if node.expanded:
                    _collapse_node(nodes, idx)
                else:
                    _expand_node(nodes, idx, ls_fn)
            else:
                screen.clear()
                return node.path
        elif key == "ESC":
            screen.clear()
            return [] if multi else ""


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
                f"Destination '{dst}' contains '..'. Paths must stay within the manifest directory."
            )
            continue
        return dst


def _ask_version(
    default_branch: str,
    branches: list[str],
    tags: list[str],
) -> tuple[str, str]:
    """Choose a version (branch / tag / SHA).

    In a TTY shows a scrollable pick list (all branches then all tags).
    Outside a TTY (CI, pipe, tests) falls back to a numbered text menu.
    """
    ordered_branches = _prioritise_default(branches, default_branch)
    ordered_tags = _sort_tags_newest_first(tags)

    # (vtype, value) — all branches first, then all tags
    choices: list[tuple[str, str]] = [
        *[("branch", b) for b in ordered_branches],
        *[("tag", t) for t in ordered_tags],
    ]

    if _is_tty() and choices:
        return _scrollable_version_pick(choices, default_branch)

    return _text_version_pick(choices, default_branch, branches, tags)


def _scrollable_version_pick(
    choices: list[tuple[str, str]],
    default_branch: str,
) -> tuple[str, str]:  # pragma: no cover – interactive TTY only
    """Scrollable version picker; falls back to free-text on Esc."""
    display: list[str] = []
    default_idx = 0
    for i, (vtype, val) in enumerate(choices):
        if vtype == "branch":
            suffix = f"  {_D}(default){_R}" if val == default_branch else ""
            display.append(f"{_CYN}{val}{_R}  {_D}branch{_R}{suffix}")
            if val == default_branch and default_idx == 0:
                default_idx = i
        else:
            display.append(f"{_MAG}{val}{_R}  {_D}tag{_R}")

    result = _scrollable_pick("Version", display, default_idx=default_idx)
    if result is not None:
        return choices[result]

    # Esc pressed — fall back to free-text
    branches = [v for t, v in choices if t == "branch"]
    tags = [v for t, v in choices if t == "tag"]
    return _text_version_pick(choices, default_branch, branches, tags)


def _text_version_pick(
    choices: list[tuple[str, str]],
    default_branch: str,
    branches: list[str],
    tags: list[str],
) -> tuple[str, str]:
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
            return ("branch", raw)
        if raw in tags:
            return ("tag", raw)

        if re.fullmatch(r"[0-9a-fA-F]{7,40}", raw):
            return ("revision", raw)

        if raw:
            return ("branch", raw)

        logger.warning("  Please enter a number or a version value.")


def _print_version_menu(choices: list[tuple[str, str]], default_branch: str) -> None:
    """Render the numbered branch/tag pick list (text fallback)."""
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

    logger.info("\n".join(lines))


def _ask_src(ls_fn: Callable[[str], list[tuple[str, bool]]]) -> str:
    """Optionally prompt for a ``src:`` sub-path or glob pattern.

    In a TTY opens a tree browser for single-path selection.
    Outside a TTY falls back to a free-text prompt.
    """
    if _is_tty():
        result = _tree_browser(
            ls_fn, "Source path  (Enter to select, Esc to skip)", multi=False
        )
        if result and isinstance(result, str):
            return result
        return ""

    return Prompt.ask(
        "  [bold]Source path[/bold]  (sub-path/glob, or Enter to fetch whole repo)",
        default="",
    ).strip()


def _ask_ignore(ls_fn: Callable[[str], list[tuple[str, bool]]]) -> list[str]:
    """Optionally prompt for ``ignore:`` paths.

    In a TTY opens a tree browser with multi-select (Space to toggle,
    Enter to confirm).  Outside a TTY falls back to a comma-separated
    free-text prompt.
    """
    if _is_tty():
        result = _tree_browser(
            ls_fn,
            "Ignore paths  (Space to select, Enter to confirm, Esc to skip)",
            multi=True,
        )
        if isinstance(result, list):
            return result
        return []

    raw = Prompt.ask(
        "  [bold]Ignore paths[/bold]  (comma-separated, or Enter to skip)",
        default="",
    ).strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


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
