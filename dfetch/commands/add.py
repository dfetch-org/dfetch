"""*Dfetch* can add projects to the manifest through the CLI.

Sometimes you want to add a project to your manifest, but you don't want to
edit the manifest by hand. With ``dfetch add`` you can add a project to your
manifest through the command line.

Non-interactive mode
--------------------
In the simplest form you just provide the URL::

    dfetch add https://github.com/some-org/some-repo.git

Dfetch will fetch the remote repository metadata (branches and tags), pick
the default branch, guess a sensible destination path based on where your
existing projects live, and append the new entry to ``dfetch.yaml``.

A confirmation prompt is shown before writing. Pass ``--force`` (or ``-f``)
to skip it::

    dfetch add -f https://github.com/some-org/some-repo.git

Interactive mode
----------------
With ``--interactive`` (or ``-i``) dfetch guides you through every manifest
field step by step::

    dfetch add -i https://github.com/some-org/some-repo.git

You will be prompted for:

* **name** – a human-readable project name (default: repository name from URL)
* **dst** – local destination directory (default: guessed from existing
  projects)
* **branch / tag / revision** – version to fetch (default: default branch of
  the remote)
* **src** – sub-path or glob inside the remote to copy (optional)

All prompts show a sensible default so you can just press *Enter* to accept
it.  When a list of choices is available (e.g. branches or tags) the list is
displayed so you can easily pick one.

The entry is appended at the end of the manifest and *not* fetched to disk;
run ``dfetch update`` afterwards to materialise the dependency.

.. scenario-include:: ../features/add-project-through-cli.feature
"""

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from rich.prompt import Prompt

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
                "Dfetch will fetch the remote branch/tag list and "
                "let you confirm or override every value."
            ),
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the add."""
        superproject = create_super_project()

        remote_url: str = args.remote_url[0]
        purl = vcs_url_to_purl(remote_url)

        # Build a minimal entry so we can probe the remote.
        probe_entry = ProjectEntry(ProjectEntryDict(name=purl.name, url=remote_url))

        # Determines VCS type, tries to reach remote.
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

        if not args.force and not _confirm():
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

    # --- version: branch / tag / revision ---
    branches = subproject.list_of_branches()
    tags = subproject.list_of_tags()

    version_type, version_value = _ask_version(default_branch, branches, tags)

    # --- src (optional) ---
    src = _ask_src()

    # Build the entry dict.
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


def _ask_name(default: str, existing_projects: Sequence[ProjectEntry]) -> str:
    """Prompt for the project name, re-asking if the name already exists."""
    existing_names = {p.name for p in existing_projects}
    while True:
        name = Prompt.ask(
            "  [bold]Project name[/bold]",
            default=default,
        )
        if name in existing_names:
            logger.warning(
                f"A project named '{name}' already exists in the manifest. "
                "Please choose a different name."
            )
        else:
            return name


def _ask_dst(name: str, default: str) -> str:
    """Prompt for the destination path."""
    suggested = default or name
    dst = Prompt.ask(
        "  [bold]Destination path[/bold] (relative to manifest)",
        default=suggested,
    )
    return dst


def _ask_version(
    default_branch: str,
    branches: list[str],
    tags: list[str],
) -> tuple[str, str]:
    """Prompt for branch, tag, or revision.

    Returns a ``(type, value)`` tuple where *type* is one of ``"branch"``,
    ``"tag"``, or ``"revision"``.
    """
    if branches:
        logger.info(
            "  [blue]Available branches:[/blue] "
            + ", ".join(f"[green]{b}[/green]" for b in branches[:10])
            + ("  …" if len(branches) > 10 else "")
        )
    if tags:
        logger.info(
            "  [blue]Available tags:[/blue]    "
            + ", ".join(f"[green]{t}[/green]" for t in tags[:10])
            + ("  …" if len(tags) > 10 else "")
        )

    version_type = Prompt.ask(
        "  [bold]Version type[/bold]",
        choices=["branch", "tag", "revision"],
        default="branch",
    )

    if version_type == "branch":
        value = Prompt.ask(
            "  [bold]Branch[/bold]",
            default=default_branch,
        )
    elif version_type == "tag":
        default_tag = tags[0] if tags else ""
        value = Prompt.ask(
            "  [bold]Tag[/bold]",
            default=default_tag,
        )
    else:
        value = Prompt.ask(
            "  [bold]Revision (full SHA)[/bold]",
        )

    return version_type, value


def _ask_src() -> str:
    """Prompt for an optional ``src:`` sub-path or glob."""
    src = Prompt.ask(
        "  [bold]Source sub-path or glob[/bold] (leave empty to fetch entire repo)",
        default="",
    )
    return src.strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _confirm() -> bool:
    """Show a confirmation prompt to the user before adding the project."""
    return (
        Prompt.ask("Add project to manifest?", choices=["y", "n"], default="y") == "y"
    )


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
