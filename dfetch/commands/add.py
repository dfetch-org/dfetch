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
from dfetch.manifest.version import Version
from dfetch.project import create_sub_project, create_super_project
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.subproject import SubProject
from dfetch.project.superproject import SuperProject
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.terminal import Entry, LsFunction
from dfetch.terminal.tree_browser import (
    BrowserConfig,
    TreeNode,
    deselected_paths,
    run_tree_browser,
    tree_pick_from_names,
    tree_single_pick,
)
from dfetch.util.purl import vcs_url_to_purl
from dfetch.util.versions import (
    is_commit_sha,
    prioritise_default,
    sort_tags_newest_first,
)

logger = get_logger(__name__)


@contextlib.contextmanager
def browse_tree(subproject: SubProject, version: str = "") -> Generator[LsFunction]:
    """Yield an ``LsFunction`` for interactively browsing *subproject*'s remote tree.

    Adapts the VCS-level ``(name, is_dir)`` tuples into :class:`~dfetch.terminal.Entry`
    objects so the terminal tree browser has no knowledge of VCS internals.

    Adds '.' as the first entry to allow selecting the repo root (which is
    treated as empty src).
    """
    if isinstance(subproject, (GitSubProject, SvnSubProject)):
        remote = subproject.remote_repo
        with remote.browse_tree(version) as vcs_ls:

            def ls(path: str = "") -> list[Entry]:
                entries = [
                    Entry(display=name, has_children=is_dir)
                    for name, is_dir in vcs_ls(path)
                ]
                if not path:
                    # Prepend "." as a selectable leaf so Enter accepts the
                    # whole repo by default; no path normalization needed.
                    return [Entry(display=".", has_children=False)] + entries
                return entries

            yield ls
    else:

        def _empty(_path: str = "") -> list[Entry]:
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

        existing_names = {p.name for p in superproject.manifest.projects}

        remote_to_use = superproject.manifest.find_remote_for_url(
            probe_entry.remote_url
        )
        if remote_to_use:
            logger.debug(
                f"Remote URL {probe_entry.remote_url} matches remote {remote_to_use.name}"
            )

        guessed_dst = superproject.manifest.guess_destination(probe_entry.name)
        default_branch = subproject.get_default_branch()

        try:
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
                    name=_unique_name(probe_entry.name, existing_names),
                    remote_url=remote_url,
                    branch=default_branch,
                    dst=guessed_dst,
                    remote_to_use=remote_to_use,
                )
                logger.print_info_line(remote_url, "Adding project to manifest")
                logger.print_yaml(project_entry.as_yaml())

            if project_entry is None:
                return

            _finalize_add(project_entry, args, superproject)
        except KeyboardInterrupt:
            logger.info(
                "  [bold bright_yellow]> Aborting add of project[/bold bright_yellow]"
            )


# ---------------------------------------------------------------------------
# Entry construction
# ---------------------------------------------------------------------------


def _finalize_add(
    project_entry: ProjectEntry,
    args: argparse.Namespace,
    superproject: SuperProject,
) -> None:
    """Write *project_entry* to the manifest and optionally run update."""
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
    version: Version,
    src: str,
    ignore: list[str],
    remote_to_use: Remote | None,
) -> ProjectEntry:
    """Assemble a ``ProjectEntry`` from the fields collected by the wizard."""
    kind, value = version.field
    entry_dict: ProjectEntryDict = ProjectEntryDict(
        name=name,
        url=remote_url,
        dst=dst,
    )
    entry_dict[kind] = value  # type: ignore[literal-required]
    if src and src != ".":
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


def _show_url_fields(
    name: str, remote_url: str, default_branch: str, remote_to_use: Remote | None
) -> None:
    """Print the fields determined solely by the URL (name, remote, url, repo-path)."""
    seed = _build_entry(
        name=name,
        remote_url=remote_url,
        dst=name,
        version=Version(branch=default_branch),
        src="",
        ignore=[],
        remote_to_use=remote_to_use,
    ).as_yaml()
    logger.print_yaml(
        {k: seed[k] for k in ("name", "remote", "url", "repo-path") if k in seed}
    )


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
    logger.print_info_line(remote_url, "Adding project through interactive wizard")

    name = _ask_name(default_name, manifest)
    _show_url_fields(name, remote_url, default_branch, remote_to_use)

    dst = _ask_dst(name, default_dst)
    if dst != name:
        logger.print_yaml_field("dst", dst)

    version = _ask_version(
        default_branch,
        subproject.list_of_branches(),
        subproject.list_of_tags(),
    )
    version_kind, version_value = version.field
    logger.print_yaml_field(version_kind, version_value)

    with browse_tree(subproject, version_value) as ls_function:
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

_PROMPT_FORMAT = "  [green]?[/green] [bold]{label}[/bold]"


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
        name = terminal.prompt("Name", suggested)
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
        dst = terminal.prompt("Destination", suggested)
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
) -> Version:
    """Choose a version (branch / tag / SHA) and return it as a :class:`~dfetch.manifest.version.Version`.

    In a TTY shows a hierarchical tree browser (names split on '/').
    Outside a TTY (CI, pipe, tests) falls back to a numbered text menu.
    """
    choices: list[Version] = [
        *[Version(branch=b) for b in prioritise_default(branches, default_branch)],
        *[Version(tag=t) for t in sort_tags_newest_first(tags)],
    ]

    if terminal.is_tty() and choices:
        return _ask_version_tree(default_branch, choices)

    return _text_version_pick(choices, default_branch)


def _ask_src(ls_function: LsFunction) -> str:
    """Optionally prompt for a ``src:`` sub-path or glob pattern.

    In a TTY opens a tree browser for single-path selection with
    directory navigation (→/← to expand/collapse).
    Outside a TTY falls back to a free-text prompt.
    """
    if terminal.is_tty():
        src = tree_single_pick(ls_function, "Source path", dirs_selectable=True)
        return "" if src == "." else src

    return Prompt.ask(
        _PROMPT_FORMAT.format(label="Source path")
        + "  (sub-path/glob, or Enter to fetch whole repo)",
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

    def _scoped_ls(path: str = "") -> list[Entry]:
        return ls_function(f"{src}/{path}" if path else src)

    browse_fn: LsFunction = _scoped_ls if src else ls_function

    if terminal.is_tty():
        while True:
            _, all_nodes = run_tree_browser(
                browse_fn,
                "Ignore",
                BrowserConfig(multi=True, all_selected=True),
            )
            ignore = deselected_paths(all_nodes)
            if not ignore:
                return []
            if _should_proceed_with_ignore(all_nodes):
                return ignore

    raw = Prompt.ask(
        _PROMPT_FORMAT.format(label="Ignore paths")
        + "  (comma-separated paths to ignore, or Enter to skip)",
        default="",
    ).strip()
    return [p.strip() for p in raw.split(",") if p.strip()]


# ---------------------------------------------------------------------------
# Version pickers
# ---------------------------------------------------------------------------


def _resolve_raw_version(raw: str, choices: list[Version]) -> Version | None:
    """Return the matching :class:`Version` from *choices*, or ``None`` when *raw* is empty.

    Checks choices first (preserving branch/tag distinction), then falls back
    to SHA detection, then treats the input as an unknown branch name.
    """
    if not raw:
        return None
    for v in choices:
        if v.field[1] == raw:
            return v
    if is_commit_sha(raw):
        return Version(revision=raw)
    return Version(branch=raw)


_MAX_LISTED = 30


def _version_menu_entries(choices: list[Version], default_branch: str) -> list[Entry]:
    """Build the numbered branch/tag pick list as :class:`~dfetch.terminal.Entry` objects."""
    entries: list[Entry] = []
    for ref in choices[:_MAX_LISTED]:
        kind, value = ref.field
        marker = (
            "  [dim](default)[/dim]"
            if value == default_branch and kind == "branch"
            else ""
        )
        display = f"{value}{marker}  [dim]{kind}[/dim]"
        entries.append(Entry(display=display, has_children=False, value=value))
    return entries


def _text_version_pick(choices: list[Version], default_branch: str) -> Version:
    """Numbered text-based version picker (non-TTY fallback and Esc fallback in TTY)."""
    entries = _version_menu_entries(choices, default_branch)
    hidden = len(choices) - len(entries)
    note = f"  [dim]  … and {hidden} more (type name directly)[/dim]" if hidden else ""

    raw = terminal.numbered_prompt(
        entries, "Version", "number, branch, tag, or SHA", default_branch, note=note
    )
    return _resolve_raw_version(raw, choices) or Version(branch=default_branch)


def _ask_version_tree(
    default_branch: str,
    choices: list[Version],
) -> Version:  # pragma: no cover - interactive TTY only
    """Branch/tag picker using the hierarchical tree browser.

    Splits names by '/' to build a navigable tree.  Falls back to the
    numbered text picker on Esc or when the selected path isn't in *choices*.
    """
    labels = {v.field[1]: v.field[0] for v in choices}
    selected = tree_pick_from_names(
        labels, "Version", priority_path=default_branch, esc_label="list"
    )
    for v in choices:
        if v.field[1] == selected:
            return v
    return _text_version_pick(choices, default_branch)
