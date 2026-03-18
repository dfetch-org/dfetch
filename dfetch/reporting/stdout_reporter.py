"""*Dfetch* can generate an report on stdout.

Depending on the state of the projects it will show as much information
from the manifest or the metadata (``.dfetch_data.yaml``).
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
