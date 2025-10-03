"""*Dfetch* can generate a software Bill-of-Materials (SBOM).

An SBOM lists the components and their supply chain relationships. Downstream
users of the software can assess the licenses used and potential risk of dependencies.

The generated SBOM can be used as input for other tools to monitor dependencies.
The tools track vulnerabilities or can enforce a license policy within an organization.

See https://cyclonedx.org/use-cases/ for more details.

*Dfetch* will try to parse the license of project, this is retained during an :ref:`Update`.

.. scenario-include:: ../features/report-sbom.feature
   :scenario:
        An fetched project generates an sbom
"""

from cyclonedx.model import ExternalReference, ExternalReferenceType, Tool, XsUri
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.license import LicenseExpression
from cyclonedx.output import make_outputter
from cyclonedx.schema import OutputFormat, SchemaVersion

import dfetch.util.purl
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.reporter import Reporter


class SbomReporter(Reporter):
    """Reporter for generating SBoM's."""

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
        purl = dfetch.util.purl.remote_url_to_purl(
            project.remote_url, version=version, subpath=project.source or None
        )

        component = Component(
            name=project.name,
            version=version,
            type=ComponentType.LIBRARY,
            purl=purl,
        )

        if purl.type == "github":
            component.external_references.add(
                ExternalReference(
                    type=ExternalReferenceType.VCS,
                    url=XsUri(f"https://github.com/{purl.namespace}/{purl.name}"),
                )
            )
        elif purl.type == "bitbucket":
            component.external_references.add(
                ExternalReference(
                    type=ExternalReferenceType.VCS,
                    url=XsUri(f"https://bitbucket.org/{purl.namespace}/{purl.name}"),
                )
            )
        else:
            component.group = purl.namespace

            vcs_url = purl.qualifiers.get("vcs_url", "")
            # ExternalReferenceType.VCS does not support ssh:// urls
            if vcs_url and "ssh://" not in vcs_url:
                component.external_references.add(
                    ExternalReference(
                        type=ExternalReferenceType.VCS,
                        url=XsUri(vcs_url),
                    )
                )

        if license_name:
            component.licenses.add(LicenseExpression(license_name))
        self._bom.components.add(component)

    def dump_to_file(self, outfile: str) -> bool:
        """Dump the SBoM to file."""
        output_format = OutputFormat(
            OutputFormat.XML if outfile.endswith(".xml") else OutputFormat.JSON
        )
        outputter = make_outputter(
            bom=self._bom,
            output_format=output_format,
            schema_version=SchemaVersion.V1_6,
        )

        outputter.output_to_file(outfile, allow_overwrite=True, indent=4)

        return True
