"""*Dfetch* can freeze the current versions of the projects.

Say you have the following manifest:

.. code-block:: yaml

    manifest:
        version: 0.0

        projects:
         - name: mymodule
           url: http://git.mycompany.local/mycompany/mymodule


As explained in :ref:`Revision/Branch/Tag` when no version is provided the latest
version of the default branch (e.g. `trunk`, `master`) of ``mymodule`` will
be fetched on a *DFetch* update_.
When your project becomes stable and you want to rely on a specific version
of ``mymodule`` you can run ``dfetch freeze``.

When the manifest lives inside a git or SVN super-project, *DFetch* edits the
manifest file **in-place** so that comments, blank lines and indentation are
preserved.  Only the version fields that changed are touched.

Otherwise *DFetch* first renames your old manifest (appended with ``.backup``).
After that a new manifest is generated with all the projects as in your original
manifest, but each with the specific version as it currently is on disk.

In our above example this would for instance result in:

.. code-block:: yaml

    manifest:
        version: 0.0

        projects:
         - name: mymodule
           url: http://git.mycompany.local/mycompany/mymodule
           tag: v1.0.0

You can also freeze a subset of projects by listing their names:

.. code-block:: sh

    dfetch freeze mymodule

.. scenario-include:: ../features/freeze-projects.feature

.. scenario-include:: ../features/freeze-specific-projects.feature

For archive projects, ``dfetch freeze`` adds the hash under the nested
``integrity.hash`` key (e.g. ``integrity.hash: sha256:<hex>``) to pin the
exact archive content used.  This value acts as the version identifier:
DFetch verifies the downloaded archive against it on every subsequent
``dfetch update``.

.. scenario-include:: ../features/freeze-archive.feature

.. scenario-include:: ../features/freeze-inplace.feature

"""

import argparse
import os
import shutil

import dfetch.commands.command
import dfetch.manifest.project
import dfetch.project
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest, update_project_in_manifest_file
from dfetch.project import create_super_project
from dfetch.project.superproject import NoVcsSuperProject
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class Freeze(dfetch.commands.command.Command):
    """Freeze your projects versions in the manifest as they are on disk.

    Generate a new manifest that has all version as they are on disk.
    Optionally pass one or more project names to freeze only those projects.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Freeze)
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to freeze (default: all projects in manifest)",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the freeze."""
        superproject = create_super_project()
        use_inplace = not isinstance(superproject, NoVcsSuperProject)

        exceptions: list[str] = []

        with in_directory(superproject.root_directory):
            for project in superproject.manifest.selected_projects(args.projects):
                with catch_runtime_exceptions(exceptions) as exceptions:
                    sub_project = dfetch.project.create_sub_project(project)
                    on_disk_version = sub_project.on_disk_version()

                    new_version = sub_project.freeze_project(project)
                    if new_version is None:
                        if on_disk_version:
                            logger.print_info_line(
                                project.name,
                                f"Already pinned in manifest on version {on_disk_version}",
                            )
                        else:
                            logger.print_warning_line(
                                project.name,
                                "No version on disk, first update with 'dfetch update'",
                            )
                    else:
                        logger.print_info_line(
                            project.name,
                            f"Frozen on version {new_version}",
                        )
                        if use_inplace:
                            update_project_in_manifest_file(
                                project, superproject.manifest.path
                            )

            if not use_inplace:
                manifest = Manifest(
                    {
                        "version": "0.0",
                        "remotes": superproject.manifest.remotes,
                        "projects": superproject.manifest.projects,
                    }
                )

                shutil.move(DEFAULT_MANIFEST_NAME, DEFAULT_MANIFEST_NAME + ".backup")

                manifest.dump(DEFAULT_MANIFEST_NAME)
                logger.info(
                    f"Updated manifest ({DEFAULT_MANIFEST_NAME}) in {os.getcwd()}"
                )
