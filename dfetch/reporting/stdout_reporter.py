"""*Dfetch* can generate an report on stdout.

Dependending on the state of the projects it will show as much information
from the manifest or the metadata (``.dfetch_data.yaml``).
"""


from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.project.metadata import Metadata
from dfetch.reporting.reporter import Reporter

logger = get_logger(__name__)


class StdoutReporter(Reporter):
    """Reporter for generating report on stdout."""

    name = "stdout"

    def add_project(
        self, project: ProjectEntry, license_name: str, version: str
    ) -> None:
        """Add a project to the report."""
        del version
        logger.print_info_field("project", project.name)
        logger.print_info_field("    remote", project.remote)
        try:
            metadata = Metadata.from_file(Metadata.from_project_entry(project).path)
            logger.print_info_field("    remote url", metadata.remote_url)
            logger.print_info_field("    branch", metadata.branch)
            logger.print_info_field("    tag", metadata.tag)
            logger.print_info_field("    last fetch", metadata.last_fetch)
            logger.print_info_field("    revision", metadata.revision)
            logger.print_info_field("    patch", metadata.patch)
            logger.print_info_field("    license", license_name)

        except FileNotFoundError:
            logger.print_info_field("    last fetch", "never")

    def dump_to_file(self, outfile: str) -> bool:
        """Do nothing."""
        del outfile
        return False
