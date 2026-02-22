"""*Dfetch* can add projects through the cli to the manifest.

Sometimes you want to add a project to your manifest, but you don't want to
edit the manifest by hand. With ``dfetch add`` you can add a project to your manifest
through the command line. This will add the project to your manifest and fetch it
to your disk. You can also specify a version to add, or it will be added with the
latest version available.

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
from dfetch.util.purl import remote_url_to_purl

logger = get_logger(__name__)


class Add(dfetch.commands.command.Command):
    """Add a new project to the manifest.

    Add a new project to the manifest.
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
            help="Remote URL of project to add",
        )

        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Always perform addition.",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the add."""
        superproject = create_super_project()

        purl = remote_url_to_purl(args.remote_url[0])
        project_entry = ProjectEntry(
            ProjectEntryDict(name=purl.name, url=args.remote_url[0])
        )

        # Determines VCS type tries to reach remote
        subproject = create_sub_project(project_entry)

        if project_entry.name in [
            project.name for project in superproject.manifest.projects
        ]:
            raise RuntimeError(
                f"Project with name {project_entry.name} already exists in manifest!"
            )

        destination = _guess_destination(
            project_entry.name, superproject.manifest.projects
        )

        if remote_to_use := _determine_remote(
            superproject.manifest.remotes, project_entry.remote_url
        ):
            logger.debug(
                f"Remote URL {project_entry.remote_url} matches remote {remote_to_use.name}"
            )

        project_entry = ProjectEntry(
            ProjectEntryDict(
                name=project_entry.name,
                url=(project_entry.remote_url),
                branch=subproject.get_default_branch(),
                dst=destination,
            ),
        )
        if remote_to_use:
            project_entry.set_remote(remote_to_use)

        logger.print_overview(
            project_entry.name,
            "Will add following entry to manifest:",
            project_entry.as_yaml(),
        )

        if not args.force and not confirm():
            logger.print_warning_line(project_entry.name, "Aborting add of project")
            return

        append_entry_manifest_file(
            (superproject.root_directory / superproject.manifest.path).absolute(),
            project_entry,
        )

        logger.print_info_line(project_entry.name, "Added project to manifest")


def confirm() -> bool:
    """Show a confirmation prompt to the user before adding the project."""
    return (
        Prompt.ask("Add project to manifest?", choices=["y", "n"], default="y") == "y"
    )


def _check_name_uniqueness(
    project_name: str, manifest_projects: Sequence[ProjectEntry]
) -> None:
    """Validate that the project name is not already used in the manifest."""
    if project_name in [project.name for project in manifest_projects]:
        raise RuntimeError(
            f"Project with name {project_name} already exists in manifest!"
        )


def _guess_destination(
    project_name: str, manifest_projects: Sequence[ProjectEntry]
) -> str:
    """Guess the destination of the project based on the remote URL and existing projects."""
    if len(manifest_projects) <= 1:
        return ""

    common_path = os.path.commonpath(
        [project.destination for project in manifest_projects]
    )

    if common_path and common_path != os.path.sep:
        return (Path(common_path) / project_name).as_posix()
    return ""


def _determine_remote(remotes: Sequence[Remote], remote_url: str) -> Remote | None:
    """Determine if the remote URL matches any of the remotes in the manifest."""
    for remote in remotes:
        if remote_url.startswith(remote.url):
            return remote
    return None
