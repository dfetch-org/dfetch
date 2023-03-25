"""*Dfetch* can generate a software Bill-of-Materials (SBOM).

An SBOM lists the components and their supply chain relationships. Downstream
users of the software can assess the licenses used and potential risk of dependencies.

The generated SBOM can be used as input for other tools to monitor dependencies.
The tools track vulnerabilities or can enforce a license policy within an organization.

See https://cyclonedx.org/use-cases/ for more details.

*Dfetch* will try to parse the license of project, this is retained during an :ref:`Update`.
"""

import json
import re
from typing import List, cast

from cyclonedx.model import (
    ExternalReference,
    ExternalReferenceType,
    LicenseChoice,
    Tool,
    XsUri,
)
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.output import get_instance
from cyclonedx.output.json import Json
from cyclonedx.schema import OutputFormat
from packageurl import PackageURL

import dfetch.util.util
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.reporter import Reporter


class SbomReporter(Reporter):
    """Reporter for generating SBoM's."""

    url_splitter = re.compile(r"([^\/)]+)")
    github_url = re.compile(r"github.com\/(?P<group>.+)\/(?P<repo>[^\s\.]+)[\.]?")
    dfetch_tool = Tool(vendor="dfetch-org", name="dfetch", version=dfetch.__version__)

    name = "SBoM"

    def __init__(self) -> None:
        """Start the report."""
        self._bom = Bom()
        self._bom.metadata.tools.add(self.dfetch_tool)

    def add_project(
        self, project: ProjectEntry, license_name: str, version: str
    ) -> None:
        """Add a project to the report."""
        match = self.github_url.search(project.remote_url)
        if match:
            component = Component(
                name=project.name,
                version=version,
                type=ComponentType.LIBRARY,
                purl=PackageURL(
                    type="github",
                    name=match.group("repo"),
                    version=version,
                    namespace=match.group("group"),
                    subpath=project.source or None,
                ),
            )
        else:
            parts = self._split_url(project.remote_url)
            component = Component(
                name=project.name,
                version=version,
                type=ComponentType.LIBRARY,
                purl=PackageURL(
                    type="generic",
                    version=version,
                    qualifiers=f"download_url={project.remote_url}",
                    namespace="/".join(parts),
                    subpath=project.source or None,
                    name=project.name,
                ),
                group="/".join(parts),
            )
            component.external_references.add(
                ExternalReference(
                    type=ExternalReferenceType.VCS,
                    url=XsUri(project.remote_url),
                )
            )

        if license_name:
            component.licenses.add(LicenseChoice(expression=license_name))
        self._bom.components.add(component)

    @staticmethod
    def _split_url(url: str) -> List[str]:
        """Split the url in elements."""
        return [
            part.group()
            for part in SbomReporter.url_splitter.finditer(url)
            if not part.group().endswith(":")  # Skip protocol specifiers
        ]

    def dump_to_file(self, outfile: str) -> bool:
        """Dump the SBoM to file."""
        output_format = (
            OutputFormat.XML if outfile.endswith(".xml") else OutputFormat.JSON
        )
        outputter = cast(Json, get_instance(bom=self._bom, output_format=output_format))

        parsed = json.loads(outputter.output_as_string())
        outputter._json_output = json.dumps(  # pylint: disable=protected-access
            parsed, indent=4
        )

        outputter.output_to_file(outfile, allow_overwrite=True)

        return True
