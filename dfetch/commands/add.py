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
import contextlib
from collections.abc import Generator

from rich.prompt import Confirm, Prompt

import dfetch.commands.command
import dfetch.manifest.project
import dfetch.project
from dfetch import terminal
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest, append_entry_manifest_file
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote
from dfetch.project import create_sub_project, create_super_project
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.subproject import SubProject
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.terminal import LsFunction
from dfetch.terminal.tree_browser import (
    TreeNode,
    deselected_paths,
    run_tree_browser,
    tree_single_pick,
)
from dfetch.util.purl import vcs_url_to_purl
from dfetch.util.versions import (
    VersionRef,
    is_commit_sha,
    prioritise_default,
    sort_tags_newest_first,
)

logger = get_logger(__name__)


@contextlib.contextmanager
def browse_tree(subproject: SubProject, version: str = "") -> Generator[LsFunction]:
    """Yield an ``LsFunction`` for interactively browsing *subproject*'s remote tree."""
    if isinstance(subproject, (GitSubProject, SvnSubProject)):
        remote = subproject._remote_repo  # pylint: disable=protected-access
        with remote.browse_tree(version) as ls_function:
            yield ls_function
    else:

        def _empty(_path: str = "") -> list[tuple[str, bool]]:
            return []

        yield _empty


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
            superproject.manifest.check_name_uniqueness(probe_entry.name)

        remote_to_use = superproject.manifest.find_remote_for_url(
            probe_entry.remote_url
        )
        if remote_to_use:
            logger.debug(
                f"Remote URL {probe_entry.remote_url} matches remote {remote_to_use.name}"
            )

        guessed_dst = superproject.manifest.guess_destination(probe_entry.name)
        default_branch = subproject.get_default_branch()

        if args.interactive:
            project_entry = _interactive_flow(
                remote_url=remote_url,
                default_name=probe_entry.name,
                default_dst=guessed_dst,
                default_branch=default_branch,
                subproject=subproject,
                remote_to_use=remote_to_use,
                manifest=superproject.manifest,
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
    entry_dict[version.kind] = version.value  # type: ignore[literal-required]
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


def _interactive_flow(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    remote_url: str,
    default_name: str,
    default_dst: str,
    default_branch: str,
    subproject: SubProject,
    remote_to_use: Remote | None,
    manifest: Manifest,
) -> ProjectEntry:
    """Guide the user through every manifest field and return a ``ProjectEntry``."""
    logger.print_info_line(default_name, f"Adding {remote_url}")

    name = _ask_name(default_name, manifest)

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
            logger.print_yaml_field(key, seed[key])  # type: ignore[arg-type]

    dst = _ask_dst(name, default_dst)
    if dst != name:
        logger.print_yaml_field("dst", dst)

    version = _ask_version(
        default_branch,
        subproject.list_of_branches(),
        subproject.list_of_tags(),
    )
    logger.print_yaml_field(version.kind, version.value)

    with browse_tree(subproject, version.value) as ls_function:
        src = _ask_src(ls_function)
        if src:
            logger.print_yaml_field("src", src)
        ignore = _ask_ignore(ls_function, src=src)
        if ignore:
            logger.print_yaml_field("ignore", ignore)

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


def _prompt(tty_label: str, rich_label: str, default: str) -> str:
    """Single-line prompt with TTY ghost text or rich fallback."""
    if terminal.is_tty():
        return terminal.ghost_prompt(tty_label, default).strip()
    return Prompt.ask(rich_label, default=default).strip()


def _unique_name(base: str, existing: set[str]) -> str:
    """Return *base* if unused, otherwise append *-1*, *-2*, … until unique."""
    if base not in existing:
        return base
    i = 1
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


def _ask_name(default: str, manifest: Manifest) -> str:
    """Prompt for the project name, re-asking on invalid input."""
    existing_names = {p.name for p in manifest.projects}
    suggested = _unique_name(default, existing_names)
    while True:
        name = _prompt("  ? Name", "  ? [bold]Name[/bold]", suggested)
        try:
            manifest.validate_project_name(name)
        except ValueError as exc:
            logger.warning(str(exc))
            if name in existing_names:
                suggested = _unique_name(name, existing_names)
            continue
        terminal.erase_last_line()
        return name


def _ask_dst(name: str, default: str) -> str:
    """Prompt for the destination path, re-asking on path-traversal attempts."""
    suggested = default or name
    while True:
        dst = _prompt(
            "  ? Destination",
            "  ? [bold]Destination[/bold] (path relative to manifest)",
            suggested,
        )
        if not dst:
            dst = name  # fall back to project name
        try:
            Manifest.validate_destination(dst)
        except ValueError as exc:
            logger.warning(str(exc))
            continue
        terminal.erase_last_line()
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
    ordered_branches = prioritise_default(branches, default_branch)
    ordered_tags = sort_tags_newest_first(tags)

    choices: list[VersionRef] = [
        *[VersionRef("branch", b) for b in ordered_branches],
        *[VersionRef("tag", t) for t in ordered_tags],
    ]

    if terminal.is_tty() and choices:
        return _ask_version_tree(default_branch, branches, tags, choices)

    return _text_version_pick(choices, default_branch, branches, tags)


def _ask_src(ls_function: LsFunction) -> str:
    """Optionally prompt for a ``src:`` sub-path or glob pattern.

    In a TTY opens a tree browser for single-path selection with
    directory navigation (→/← to expand/collapse).
    Outside a TTY falls back to a free-text prompt.
    """
    if terminal.is_tty():
        return tree_single_pick(
            ls_function, "Source path  (Enter to select, Esc to skip)"
        )

    return Prompt.ask(
        "  ? [bold]Source path[/bold]  (sub-path/glob, or Enter to fetch whole repo)",
        default="",
    ).strip()


def _should_proceed_with_ignore(nodes: list[TreeNode]) -> bool:
    """Warn and confirm when every visible node has been deselected."""
    if any(n.selected for n in nodes):
        return True
    logger.warning(
        "You have deselected everything. This will ignore all files in the project."
    )
    return bool(Confirm.ask("Continue with empty selection?", default=False))


def _ask_ignore(ls_function: LsFunction, src: str = "") -> list[str]:
    """Optionally prompt for ``ignore:`` paths.

    Opens a tree browser (TTY) or falls back to free-text.  All items start
    selected (= keep).  Deselect items to mark them for ignoring.

    Paths are returned relative to *src* when *src* is set, otherwise relative
    to the repo root.
    """

    def _scoped_ls(path: str = "") -> list[tuple[str, bool]]:
        return ls_function(f"{src}/{path}" if path else src)

    browse_fn: LsFunction = _scoped_ls if src else ls_function

    if terminal.is_tty():
        while True:
            _, all_nodes = run_tree_browser(
                browse_fn,
                "Ignore  (Space deselects → ignored, Enter confirms, Esc skips)",
                multi=True,
                all_selected=True,
            )
            ignore = deselected_paths(all_nodes)
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


def _version_ls_function(
    branches: list[str],
    tags: list[str],
    default_branch: str,
) -> LsFunction:
    """Build a ls_function that exposes branches and tags as a /-split tree.

    Leaf nodes carry a dim kind label (``branch`` / ``tag``) so they are
    visually distinct from directory segments.  The tree browser strips ANSI
    when building ``node.path``, so the stored path is always the clean name.
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

    Splits names by '/' to build a navigable tree.  Falls back to the
    numbered text picker on Esc or when the path can't be resolved.
    """
    ls = _version_ls_function(branches, tags, default_branch)
    selected = tree_single_pick(ls, "Version  (Enter to select · Esc to type freely)")

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

    branch_set = set(branches)
    tag_set = set(tags)

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

        if raw in branch_set:
            return VersionRef("branch", raw)
        if raw in tag_set:
            return VersionRef("tag", raw)
        if is_commit_sha(raw):
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
