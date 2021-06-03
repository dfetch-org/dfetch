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

First *DFetch* will rename your old manifest (appended with ``.backup``).
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

"""

import argparse
import os
import shutil
from typing import List

import dfetch.commands.command
import dfetch.manifest.project
import dfetch.project
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest, get_manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class Freeze(dfetch.commands.command.Command):
    """Freeze your projects versions in the manifest as they are on disk.

    Generate a new manifest that has all version as they are on disk.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Freeze)

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the freeze."""
        del args  # unused

        manifest, path = get_manifest()

        exceptions: List[str] = []
        projects: List[ProjectEntry] = []

        with in_directory(os.path.dirname(path)):
            for project in manifest.projects:
                with catch_runtime_exceptions(exceptions) as exceptions:
                    on_disk_version = dfetch.project.make(project).on_disk_version()

                    if project.version == on_disk_version:
                        logger.print_info_line(
                            project.name,
                            f"Already pinned in manifest on version {project.version}",
                        )
                    elif on_disk_version:
                        logger.print_info_line(
                            project.name, f"Freezing on version {on_disk_version}"
                        )
                        project.version = on_disk_version
                    else:
                        logger.print_warning_line(
                            project.name,
                            "No version on disk, first update with 'dfetch update'",
                        )

                    projects.append(project)

            manifest = Manifest(
                {"version": "0.0", "remotes": manifest.remotes, "projects": projects}
            )

            shutil.move(DEFAULT_MANIFEST_NAME, DEFAULT_MANIFEST_NAME + ".backup")

            manifest.dump(DEFAULT_MANIFEST_NAME)
            logger.info(f"Updated manifest ({DEFAULT_MANIFEST_NAME}) in {os.getcwd()}")
