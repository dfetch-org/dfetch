"""*Dfetch* can generate an SBoM, see https://cyclonedx.org/use-cases/ for more details."""

import re

from cyclonedx.model import ExternalReference, ExternalReferenceType
from cyclonedx.model.bom import Bom, Tool
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.output import OutputFormat, get_instance

import dfetch
import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.util.util
from dfetch.manifest.project import ProjectEntry


class SbomReporter:
    """Reporter for generating SBoM's."""

    github_url = re.compile(r"github.com\/(?P<group>.+)\/(?P<repo>[^\s\.]+)[\.]?")
    dfetch_tool = Tool(vendor="dfetch-org", name="dfetch", version=dfetch.__version__)

    name = "SBoM"

    def __init__(self) -> None:
        """Start the report."""
        self._bom = Bom()
        self._bom.get_metadata().add_tool(self.dfetch_tool)

    def add_project(self, project: ProjectEntry, license: str, version: str) -> None:
        """Add a project to the report."""
        match = self.github_url.search(project.remote_url)
        if match:
            component = Component(
                name=match.group("repo"),
                version=version,
                component_type=ComponentType.LIBRARY,
                package_url_type="github",
                namespace=match.group("group"),
                subpath=project._src or None,
            )
        else:
            component = Component(
                name=project.name,
                version=version,
                component_type=ComponentType.LIBRARY,
                package_url_type="generic",
                qualifiers=f"download_url={project.remote_url}",
                subpath=project._src or None,
            )
            component.add_external_reference(
                ExternalReference(
                    reference_type=ExternalReferenceType.VCS,
                    url=project.remote_url,
                )
            )

        component.set_license(license)
        self._bom.add_component(component)

    def dump_to_file(self, outfile: str) -> None:
        """Dump the SBoM to file."""
        output_format = (
            OutputFormat.XML if outfile.endswith(".xml") else OutputFormat.JSON
        )
        outputter = get_instance(bom=self._bom, output_format=output_format)
        outputter.output_to_file(outfile, allow_overwrite=True)
