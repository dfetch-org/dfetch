"""*Dfetch* can generate a report on stdout.

The stdout report prints one block per project. Fields are drawn from the
manifest where possible and fall back to the ``.dfetch_data.yaml`` metadata
written by :ref:`Update` when the project has been fetched at least once.

Output format
~~~~~~~~~~~~~

A typical block looks like this:

.. code-block:: console

   my-project:
   - remote            : <none>
     remote url        : https://github.com/example/my-project
     branch            : main
     tag               : <none>
     last fetch        : 01/01/2025, 12:00:00
     revision          : e1fda19a…
     patch             : <none>
     licenses          : MIT

The fields are:

- **remote**: named :ref:`Remotes` entry from the manifest (``<none>`` when
  the URL is given directly via ``url:``).
- **remote url**: full URL of the upstream repository (derived from ``url:``
  or the ``url-base`` of the :ref:`Remotes` entry).
- **branch** / **tag** / **revision**: version as recorded at fetch time;
  see :ref:`Revision/Branch/Tag`.
- **last fetch**: timestamp of the last successful ``dfetch update``.
- **patch**: patch file(s) applied after fetching (``<none>`` if unused);
  see :ref:`Patch`.
- **licenses**: license(s) auto-detected in the fetched directory.

If a project has never been fetched the metadata file is absent and only
``last fetch: never`` is shown.

Dependencies
~~~~~~~~~~~~

When a fetched git project contains submodules, *Dfetch* records each one as a
dependency inside the project's ``.dfetch_data.yaml`` metadata file. The
stdout report surfaces these under a ``dependencies`` block:

.. code-block:: console

   my-project:
   - remote            : <none>
     ...
     dependencies      :
     - path            : ext/vendor-lib
       url             : https://github.com/example/vendor-lib
       branch          : master
       tag             : <none>
       revision        : 79698c99…
       source-type     : git-submodule

Each dependency entry contains:

- **path**: location of the submodule inside the fetched project.
- **url**: upstream URL of the submodule repository.
- **branch** / **tag** / **revision**: version information pinned by the parent.
- **source-type**: origin of the dependency (e.g. ``git-submodule``).

.. scenario-include:: ../features/fetch-git-repo-with-submodule.feature
    :scenario: Submodule changes are reported in the project report
"""

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.project.metadata import Metadata
from dfetch.reporting.reporter import Reporter
from dfetch.util.license import License

logger = get_logger(__name__)


class StdoutReporter(Reporter):
    """Reporter for generating report on stdout."""

    name = "stdout"

    def add_project(
        self,
        project: ProjectEntry,
        licenses: list[License],
        version: str,
    ) -> None:
        """Add a project to the report."""
        del version
        logger.print_info_line(project.name, "")
        logger.print_info_field("- remote", project.remote)
        try:
            metadata = Metadata.from_file(Metadata.from_project_entry(project).path)
            logger.print_info_field("  remote url", metadata.remote_url)
            logger.print_info_field("  branch", metadata.branch)
            logger.print_info_field("  tag", metadata.tag)
            logger.print_info_field("  last fetch", str(metadata.last_fetch))
            logger.print_info_field("  revision", metadata.revision)
            logger.print_info_field("  patch", ", ".join(metadata.patch))
            logger.print_info_field(
                "  licenses", ",".join(license.name for license in licenses)
            )

            if metadata.dependencies:
                logger.info("")
                logger.print_report_line("  dependencies", "")
            for dependency in metadata.dependencies:
                logger.print_info_field("  - path", dependency.get("destination", ""))
                logger.print_info_field("    url", dependency.get("remote_url", ""))
                logger.print_info_field("    branch", dependency.get("branch", ""))
                logger.print_info_field("    tag", dependency.get("tag", ""))
                logger.print_info_field("    revision", dependency.get("revision", ""))
                logger.print_info_field(
                    "    source-type", dependency.get("source_type", "")
                )
                logger.info("")

        except FileNotFoundError:
            logger.print_info_field("  last fetch", "never")

    def dump_to_file(self, outfile: str) -> bool:
        """Do nothing."""
        del outfile
        return False
