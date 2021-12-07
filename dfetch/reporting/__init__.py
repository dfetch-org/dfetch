"""Various reporters for generating reports."""

from enum import Enum
from typing import Dict, Type

from dfetch.reporting.reporter import Reporter
from dfetch.reporting.sbom_reporter import SbomReporter
from dfetch.reporting.stdout_reporter import StdoutReporter


class ReportTypes(Enum):
    """Enum giving a name to a type of reporter."""

    SBOM = "sbom"
    STDOUT = "list"

    def __str__(self) -> str:
        """Get the string."""
        return self.value


REPORTERS: Dict[ReportTypes, Type[Reporter]] = {
    ReportTypes.STDOUT: StdoutReporter,
    ReportTypes.SBOM: SbomReporter,
}
