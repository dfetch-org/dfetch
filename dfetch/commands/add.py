# pylint: disable=too-many-lines
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

* **name** - defaults to the repository name extracted from the URL
* **dst** - local destination; defaults to a path guessed from existing projects
* **version** - scrollable list of all branches and tags (arrow keys to
  navigate, Enter to select, Esc to fall back to free-text input)
* **src** - optional sub-path; browse the remote tree with arrow keys,
  expand/collapse folders with Enter/Right/Left
* **ignore** - optional list of paths to exclude; same tree browser with
  Space to toggle multiple selections and Enter to confirm

After confirming the add you are offered to run ``dfetch update`` immediately
so the dependency is materialised without a separate command.

.. scenario-include:: ../features/add-project-through-cli.feature
"""

from __future__ import annotations

import argparse
import os
import re
import sys
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
from dfetch.util import terminal
from dfetch.util.purl import vcs_url_to_purl

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

        if not args.interactive:
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

        if not args.force and not Confirm.ask("Add project to manifest?", default=True):
            logger.info(
                "  [bold bright_yellow]> Aborting add of project[/bold bright_yellow]"
            )
            return

        append_entry_manifest_file(
            (superproject.root_directory / superproject.manifest.path).absolute(),
            project_entry,
        )

        logger.print_info_line(
            project_entry.name,
            f"Added '{project_entry.name}' to manifest '{superproject.manifest.path}'",
        )

        # Offer to run update immediately (only when we already prompted the user,
        # i.e. not in --force mode where we want zero interaction).
        if not args.force and Confirm.ask(
            f"Run 'dfetch update {project_entry.name}' now?", default=True
        ):
            # pylint: disable=import-outside-toplevel
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


def _build_entry(  # pylint: disable=too-many-arguments
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


def _print_yaml_field(key: str, value: str | list[str]) -> None:
    """Print one manifest field in YAML style."""
    if isinstance(value, list):
        logger.info(f"  [blue]{key}:[/blue]")
        for item in value:
            logger.info(f"    - {item}")
    else:
        logger.info(f"  [blue]{key}:[/blue] {value}")


def _interactive_flow(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    remote_url: str,
    default_name: str,
    default_dst: str,
    default_branch: str,
    subproject: SubProject,
    remote_to_use: Remote | None,
    existing_projects: Sequence[ProjectEntry],
) -> ProjectEntry:
    """Guide the user through every manifest field and return a ``ProjectEntry``."""
    logger.print_info_line(default_name, f"Adding {remote_url}")

    name = _ask_name(default_name, existing_projects)

    # Show the fields that are fixed by the URL right after the name is confirmed.
    seed = _build_entry(
        name=name,
        remote_url=remote_url,
        dst=name,
        version=VersionRef("branch", default_branch),
        src="",
        ignore=[],
        remote_to_use=remote_to_use,
    ).as_yaml()
    for key in ("name", "remote", "url", "repo-path"):
        if key in seed and isinstance(seed[key], (str, list)):
            _print_yaml_field(key, seed[key])  # type: ignore[arg-type]

    dst = _ask_dst(name, default_dst)
    if dst != name:
        _print_yaml_field("dst", dst)

    version = _ask_version(
        default_branch,
        subproject.list_of_branches(),
        subproject.list_of_tags(),
    )
    _print_yaml_field(version.kind, version.value)

    with subproject.browse_tree(version.value) as ls_fn:
        src = _ask_src(ls_fn)
        if src:
            _print_yaml_field("src", src)
        ignore = _ask_ignore(ls_fn, src=src)
        if ignore:
            _print_yaml_field("ignore", ignore)

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


def _erase_prompt_line() -> None:
    """Erase the last printed line (the rich prompt) when running in a TTY."""
    if terminal.is_tty():
        sys.stdout.write("\x1b[1A\x1b[2K")
        sys.stdout.flush()


def _unique_name(base: str, existing: set[str]) -> str:
    """Return *base* if unused, otherwise *base*-1, *base*-2, … until unique."""
    if base not in existing:
        return base
    i = 1
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


def _ask_name(default: str, existing_projects: Sequence[ProjectEntry]) -> str:
    """Prompt for the project name, re-asking on invalid input."""
    existing_names = {p.name for p in existing_projects}
    suggested = _unique_name(default, existing_names)
    while True:
        if terminal.is_tty():
            name = terminal.ghost_prompt("  ? Name", suggested).strip()
        else:
            name = Prompt.ask("  ? [bold]Name[/bold]", default=suggested).strip()
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
            suggested = _unique_name(name, existing_names)
            continue
        _erase_prompt_line()
        return name


def _ask_dst(name: str, default: str) -> str:
    """Prompt for the destination path, re-asking on path-traversal attempts."""
    suggested = default or name
    while True:
        if terminal.is_tty():
            dst = terminal.ghost_prompt("  ? Destination", suggested).strip()
        else:
            dst = Prompt.ask(
                "  ? [bold]Destination[/bold] (path relative to manifest)",
                default=suggested,
            ).strip()
        if not dst:
            dst = name  # fall back to project name
        if any(part == ".." for part in Path(dst).parts):
            logger.warning(
                f"Destination '{dst}' contains '..'. "
                "Paths must stay within the manifest directory."
            )
            continue
        _erase_prompt_line()
        return dst


def _ask_version(
    default_branch: str,
    branches: list[str],
    tags: list[str],
) -> VersionRef:
    """Choose a version (branch / tag / SHA) and return it as a ``VersionRef``.

    In a TTY shows a hierarchical tree browser (names split on '/').
    Outside a TTY (CI, pipe, tests) falls back to a numbered text menu.
    """
    ordered_branches = _prioritise_default(branches, default_branch)
    ordered_tags = _sort_tags_newest_first(tags)

    choices: list[VersionRef] = [
        *[VersionRef("branch", b) for b in ordered_branches],
        *[VersionRef("tag", t) for t in ordered_tags],
    ]

    if terminal.is_tty() and choices:
        return _ask_version_tree(default_branch, branches, tags, choices)

    return _text_version_pick(choices, default_branch, branches, tags)


def _ask_src(ls_fn: LsFn) -> str:
    """Optionally prompt for a ``src:`` sub-path or glob pattern.

    In a TTY opens a tree browser for single-path selection with
    directory navigation (→/← to expand/collapse).
    Outside a TTY falls back to a free-text prompt.
    """
    if terminal.is_tty():
        return _tree_single_pick(ls_fn, "Source path  (Enter to select, Esc to skip)")

    return Prompt.ask(
        "  ? [bold]Source path[/bold]  (sub-path/glob, or Enter to fetch whole repo)",
        default="",
    ).strip()


def _normalize_ignore_paths(ignore: list[str], src: str) -> list[str]:
    """Strip the *src* prefix from each path so paths are relative to *src*."""
    if not src:
        return ignore
    prefix = src.rstrip("/") + "/"
    return [p[len(prefix) :] if p.startswith(prefix) else p for p in ignore]


def _should_proceed_with_ignore(nodes: list[_TreeNode]) -> bool:
    """Return True when the ignore list is acceptable to use.

    If the user deselected every visible node, warn and ask for confirmation.
    """
    if any(n.selected for n in nodes):
        return True
    logger.warning(
        "You have deselected everything. This will ignore all files in the project."
    )
    return bool(Confirm.ask("Continue with empty selection?", default=False))


def _ask_ignore(ls_fn: LsFn, src: str = "") -> list[str]:
    """Optionally prompt for ``ignore:`` paths.

    Opens a tree browser (TTY) or falls back to free-text.  All items start
    selected (= keep).  Deselect items to mark them for ignoring.

    Paths are returned relative to *src* when *src* is set, otherwise relative
    to the repo root.
    """

    def _scoped_ls(path: str = "") -> list[tuple[str, bool]]:
        return ls_fn(f"{src}/{path}" if path else src)

    browse_fn: LsFn = _scoped_ls if src else ls_fn

    if terminal.is_tty():
        while True:
            all_nodes: list[_TreeNode] = []
            _run_tree_browser(
                browse_fn,
                "Ignore  (Space deselects → ignored, Enter confirms, Esc skips)",
                multi=True,
                all_selected=True,
                _out_nodes=all_nodes,
            )
            ignore = _compute_ignore_from_nodes(all_nodes)
            if not ignore:
                return []
            if _should_proceed_with_ignore(all_nodes):
                return ignore

    raw = Prompt.ask(
        "  ? [bold]Ignore paths[/bold]  (comma-separated paths to ignore, or Enter to skip)",
        default="",
    ).strip()
    return [p.strip() for p in raw.split(",") if p.strip()] if raw else []


# ---------------------------------------------------------------------------
# Version pickers
# ---------------------------------------------------------------------------


def _version_ls_fn(
    branches: list[str],
    tags: list[str],
    default_branch: str,
) -> LsFn:
    """Build a ls_fn that exposes branches and tags as a /-split tree.

    Leaf nodes (actual branch/tag names) carry ANSI colour in their display
    name (cyan = branch, magenta = tag).  ``_expand_node`` and
    ``_run_tree_browser`` strip ANSI when building ``node.path``, so the
    stored path is always the clean version name.
    """
    leaf_kind: dict[str, str] = {b: "branch" for b in branches}
    leaf_kind.update({t: "tag" for t in tags})
    all_names: list[str] = sorted(leaf_kind)

    def ls(path: str) -> list[tuple[str, bool]]:
        prefix = (path + "/") if path else ""
        seen: dict[str, bool] = {}  # first segment → is_dir

        for name in all_names:
            if not name.startswith(prefix):
                continue
            rest = name[len(prefix) :]
            if not rest:
                continue
            seg = rest.split("/")[0]
            if seg in seen:
                continue
            full = prefix + seg
            seen[seg] = any(n.startswith(full + "/") for n in all_names)

        def _sort_key(seg: str) -> tuple[int, str]:
            full = prefix + seg
            on_default_path = full == default_branch or default_branch.startswith(
                full + "/"
            )
            return (0 if on_default_path else 1, seg)

        result: list[tuple[str, bool]] = []
        for seg in sorted(seen, key=_sort_key):
            full = prefix + seg
            if seen[seg]:  # is_dir
                result.append((seg, True))
            else:
                kind = leaf_kind[full]
                default_marker = (
                    f" {terminal.DIM}(default){terminal.RESET}"
                    if full == default_branch
                    else ""
                )
                result.append(
                    (
                        f"{seg} {terminal.DIM}{kind}{terminal.RESET}{default_marker}",
                        False,
                    )
                )

        return result

    return ls


def _ask_version_tree(
    default_branch: str,
    branches: list[str],
    tags: list[str],
    choices: list[VersionRef],
) -> VersionRef:  # pragma: no cover - interactive TTY only
    """Branch/tag picker using the hierarchical tree browser.

    Splits names by '/' to build a navigable tree (e.g. ``feature/login``
    appears as ``feature ▸ login``).  Leaves are cyan for branches and
    magenta for tags.  Falls back to the numbered text picker on Esc or
    when the selected path cannot be resolved to a known version.
    """
    ls = _version_ls_fn(branches, tags, default_branch)
    selected = _tree_single_pick(ls, "Version  (Enter to select · Esc to type freely)")

    branch_set = set(branches)
    tag_set = set(tags)
    if selected in branch_set:
        return VersionRef("branch", selected)
    if selected in tag_set:
        return VersionRef("tag", selected)

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
            "  ? [bold]Version[/bold]  (number, branch, tag, or SHA)",
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
                path=f"{node.path}/{terminal.strip_ansi(name)}",
                is_dir=is_dir,
                depth=node.depth + 1,
                selected=node.selected,
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
    nodes[idx].children_loaded = False


def _render_tree_lines(
    nodes: list[_TreeNode], idx: int, top: int, *, ignore_mode: bool = False
) -> list[str]:
    """Build the list of display strings for one frame of the tree browser."""
    n = len(nodes)
    lines: list[str] = []
    for i in range(top, min(top + terminal.VIEWPORT, n)):
        node = nodes[i]
        indent = "  " * node.depth
        icon = ("▾ " if node.expanded else "▸ ") if node.is_dir else "  "
        cursor = f"{terminal.YELLOW}▶{terminal.RESET}" if i == idx else " "
        if ignore_mode:
            name = (
                f"{terminal.DIM}{node.name}{terminal.RESET}"
                if not node.selected
                else node.name
            )
            lines.append(f"  {cursor} {indent}{icon}{name}")
        else:
            check = f"{terminal.GREEN}✓ {terminal.RESET}" if node.selected else "  "
            name = (
                f"{terminal.BOLD}{node.name}{terminal.RESET}" if i == idx else node.name
            )
            lines.append(f"  {cursor} {check}{indent}{icon}{name}")
    return lines


def _cascade_selection(nodes: list[_TreeNode], parent_idx: int, selected: bool) -> None:
    """Set *selected* on all loaded descendants of the node at *parent_idx*."""
    parent_depth = nodes[parent_idx].depth
    for i in range(parent_idx + 1, len(nodes)):
        if nodes[i].depth <= parent_depth:
            break
        nodes[i].selected = selected


def _adjust_scroll(idx: int, top: int) -> int:
    """Return a new *top* so that *idx* is within the visible viewport."""
    if idx < top:
        return idx
    if idx >= top + terminal.VIEWPORT:
        return idx - terminal.VIEWPORT + 1
    return top


def _build_tree_frame(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    title: str,
    nodes: list[_TreeNode],
    idx: int,
    top: int,
    hint: str,
    *,
    ignore_mode: bool = False,
) -> list[str]:
    """Build all display lines for one render frame of the tree browser."""
    n = len(nodes)
    header = [f"  {terminal.BOLD}{title}{terminal.RESET}"]
    if top > 0:
        header.append(f"    {terminal.DIM}↑ {top} more above{terminal.RESET}")
    body = _render_tree_lines(nodes, idx, top, ignore_mode=ignore_mode)
    footer: list[str] = []
    remaining = n - (top + terminal.VIEWPORT)
    if remaining > 0:
        footer.append(f"    {terminal.DIM}↓ {remaining} more below{terminal.RESET}")
    footer.append(f"  {terminal.DIM}{hint}{terminal.RESET}")
    return header + body + footer


def _handle_tree_nav(key: str, idx: int, n: int) -> int | None:
    """Handle arrow/page navigation keys; return new index or None if not a nav key."""
    if key == "UP":
        return max(0, idx - 1)
    if key == "DOWN":
        return min(n - 1, idx + 1)
    if key == "PGUP":
        return max(0, idx - terminal.VIEWPORT)
    if key == "PGDN":
        return min(n - 1, idx + terminal.VIEWPORT)
    return None


def _handle_tree_left(nodes: list[_TreeNode], idx: int) -> int:
    """Handle the LEFT key: collapse the current dir or jump to its parent."""
    node = nodes[idx]
    if node.is_dir and node.expanded:
        _collapse_node(nodes, idx)
        return idx
    if node.depth > 0:
        for i in range(idx - 1, -1, -1):
            if nodes[i].depth < node.depth:
                return i
    return idx


def _handle_tree_space(
    nodes: list[_TreeNode], idx: int, multi: bool
) -> list[str] | None:
    """Handle SPACE: toggle selection (multi) or select immediately (single).

    Returns a path list when the browser should exit, or ``None`` to continue.
    """
    node = nodes[idx]
    if multi:
        node.selected = not node.selected
        if node.is_dir:
            _cascade_selection(nodes, idx, node.selected)
        return None
    return [node.path]


def _handle_tree_enter(
    nodes: list[_TreeNode], idx: int, ls_fn: LsFn, multi: bool
) -> tuple[int, list[str] | None]:
    """Handle ENTER: confirm selection (multi), expand/collapse dir, or pick file."""
    node = nodes[idx]
    if multi:
        return idx, [n.path for n in nodes if n.selected]
    if node.is_dir:
        if node.expanded:
            _collapse_node(nodes, idx)
        else:
            _expand_node(nodes, idx, ls_fn)
        return idx, None
    return idx, [node.path]


def _handle_tree_action(
    key: str,
    nodes: list[_TreeNode],
    idx: int,
    ls_fn: LsFn,
    multi: bool,
) -> tuple[int, list[str] | None]:
    """Dispatch non-navigation keypresses.

    Returns ``(new_idx, result)``.  When *result* is not ``None`` the browser
    should exit and return it (``[]`` for ESC/skip, path list for a selection).
    """
    node = nodes[idx]
    if key == "RIGHT":
        if node.is_dir and not node.expanded:
            _expand_node(nodes, idx, ls_fn)
        return idx, None
    if key == "LEFT":
        return _handle_tree_left(nodes, idx), None
    if key == "SPACE":
        return idx, _handle_tree_space(nodes, idx, multi)
    if key == "ENTER":
        return _handle_tree_enter(nodes, idx, ls_fn, multi)
    if key == "ESC":
        return idx, []
    return idx, None


def _run_tree_browser(
    ls_fn: LsFn,
    title: str,
    *,
    multi: bool,
    all_selected: bool = False,
    _out_nodes: list[_TreeNode] | None = None,
) -> list[str]:  # pragma: no cover - interactive TTY only
    """Core tree browser loop.

    Returns a list of selected paths.  In single-select mode the list has
    at most one item; in multi-select mode it may have any number.
    If ``all_selected=True``, all nodes start selected.
    If ``_out_nodes`` is provided, it is extended with the final node state on exit.
    """
    root_entries = ls_fn("")
    if not root_entries:
        return []

    nodes: list[_TreeNode] = [
        _TreeNode(
            name=name,
            path=terminal.strip_ansi(name),
            is_dir=is_dir,
            depth=0,
            selected=all_selected,
        )
        for name, is_dir in root_entries
    ]
    hint = (
        "↑/↓ navigate  Space select  Enter confirm  →/← expand/collapse  Esc skip"
        if multi
        else "↑/↓ navigate  Enter/Space select  →/← expand/collapse  Esc skip"
    )
    screen = terminal.Screen()
    idx, top = 0, 0

    while True:
        n = len(nodes)
        if n == 0:
            screen.clear()
            return []
        idx = max(0, min(idx, n - 1))
        top = _adjust_scroll(idx, top)
        screen.draw(
            _build_tree_frame(title, nodes, idx, top, hint, ignore_mode=all_selected)
        )
        key = terminal.read_key()

        new_idx = _handle_tree_nav(key, idx, n)
        if new_idx is not None:
            idx = new_idx
            continue

        idx, result = _handle_tree_action(key, nodes, idx, ls_fn, multi)
        if result is not None:
            if _out_nodes is not None:
                _out_nodes.extend(nodes)
            screen.clear()
            return result


def _tree_single_pick(ls_fn: LsFn, title: str) -> str:
    """Browse the remote tree and return a single selected path.

    Returns ``""`` if the user skips (Esc) or no tree is available.
    """
    result = _run_tree_browser(ls_fn, title, multi=False)
    return result[0] if result else ""


def _all_descendants_deselected(nodes: list[_TreeNode], parent_idx: int) -> bool:
    """Return True if every loaded descendant of the node at *parent_idx* is deselected."""
    parent_depth = nodes[parent_idx].depth
    for i in range(parent_idx + 1, len(nodes)):
        if nodes[i].depth <= parent_depth:
            break
        if nodes[i].selected:
            return False
    return True


def _compute_ignore_from_nodes(nodes: list[_TreeNode]) -> list[str]:
    """Compute the minimal ignore list from the final browser node state.

    A deselected directory is emitted as a single entry when all its loaded
    descendants are also deselected (or it was never expanded).  This keeps
    the ignore list short.  Individual deselected files are listed when their
    parent directory is only partially deselected.
    """
    ignore: list[str] = []
    ignored_dirs: set[str] = set()

    for i, node in enumerate(nodes):
        if node.selected:
            continue
        if any(node.path.startswith(d + "/") for d in ignored_dirs):
            continue
        if node.is_dir and (
            not node.children_loaded or _all_descendants_deselected(nodes, i)
        ):
            ignore.append(node.path)
            ignored_dirs.add(node.path)
        elif not node.is_dir:
            ignore.append(node.path)

    return ignore


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
        key=_semver_key,  # type: ignore[arg-type, return-value]
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
