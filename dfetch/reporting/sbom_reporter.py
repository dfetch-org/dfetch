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

from decimal import Decimal
from typing import List

from cyclonedx.builder.this import this_component as cdx_lib_component
from cyclonedx.model import ExternalReference, ExternalReferenceType, XsUri
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.component_evidence import (
    AnalysisTechnique,
    ComponentEvidence,
    Identity,
    IdentityField,
    Method,
    Occurrence,
)
from cyclonedx.model.contact import OrganizationalEntity
from cyclonedx.model.license import DisjunctiveLicense as CycloneDxLicense
from cyclonedx.output import make_outputter
from cyclonedx.schema import OutputFormat, SchemaVersion

import dfetch.util.purl
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.reporter import Reporter
from dfetch.util.license import License

# PyRight is pedantic with decorators see https://github.com/madpah/serializable/issues/8
# It might be fixable with https://github.com/microsoft/pyright/discussions/4426, would prefer
# upstream fix, for now suppress, mypy will keep us safe.
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false


class SbomReporter(Reporter):
    """Reporter for generating SBoM's."""

    dfetch_tool = Component(
        type=ComponentType.APPLICATION,
        supplier=OrganizationalEntity(name="dfetch-org"),
        name="dfetch",
        version=dfetch.__version__,
        bom_ref=f"dfetch-{dfetch.__version__}",
        licenses=[CycloneDxLicense(name="MIT License", id="MIT")],
        external_references=[
            ExternalReference(
                type=ExternalReferenceType.VCS,
                url=XsUri("https://github.com/dfetch-org/dfetch"),
            ),
            ExternalReference(
                type=ExternalReferenceType.BUILD_SYSTEM,
                url=XsUri("https://github.com/dfetch-org/dfetch/actions"),
            ),
            ExternalReference(
                type=ExternalReferenceType.ISSUE_TRACKER,
                url=XsUri("https://github.com/dfetch-org/dfetch/issues"),
            ),
            ExternalReference(
                type=ExternalReferenceType.DISTRIBUTION,
                url=XsUri("https://pypi.org/project/dfetch/"),
            ),
            ExternalReference(
                type=ExternalReferenceType.DOCUMENTATION,
                url=XsUri("https://dfetch.readthedocs.io/"),
            ),
            ExternalReference(
                type=ExternalReferenceType.LICENSE,
                url=XsUri("https://github.com/dfetch-org/dfetch/blob/main/LICENSE"),
            ),
            ExternalReference(
                type=ExternalReferenceType.RELEASE_NOTES,
                url=XsUri(
                    "https://github.com/dfetch-org/dfetch/blob/main/CHANGELOG.rst"
                ),
            ),
            ExternalReference(
                type=ExternalReferenceType.WEBSITE,
                url=XsUri("https://dfetch-org.github.io/"),
            ),
        ],
    )

    name = "SBoM"

    def __init__(self) -> None:
        """Start the report."""
        self._bom = Bom()
        self._bom.metadata.tools.components.add(self.dfetch_tool)
        self._bom.metadata.tools.components.add(cdx_lib_component())

    def add_project(
        self,
        project: ProjectEntry,
        licenses: List[License],
        version: str,
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
            evidence=ComponentEvidence(
                occurrences=[Occurrence(location="dfetch.yaml")],
                identity=[
                    Identity(
                        field=IdentityField.NAME,
                        tools=[self.dfetch_tool.bom_ref],
                        methods=[
                            Method(
                                technique=AnalysisTechnique.MANIFEST_ANALYSIS,
                                confidence=Decimal.from_float(0.4),
                                value="Name as used for project in dfetch.yaml",
                            )
                        ],
                        concluded_value=project.name,
                    ),
                    Identity(
                        field=IdentityField.VERSION,
                        tools=[self.dfetch_tool.bom_ref],
                        methods=[
                            Method(
                                technique=AnalysisTechnique.MANIFEST_ANALYSIS,
                                confidence=Decimal.from_float(0.4),
                                value="Version as used for project in dfetch.yaml",
                            )
                        ],
                        concluded_value=version,
                    ),
                    Identity(
                        field=IdentityField.PURL,
                        tools=[self.dfetch_tool.bom_ref],
                        methods=[
                            Method(
                                technique=AnalysisTechnique.MANIFEST_ANALYSIS,
                                confidence=Decimal.from_float(0.4),
                                value="Determined from the VCS url as used for project in dfetch.yaml",
                            )
                        ],
                        concluded_value=purl.to_string(),
                    ),
                ],
            ),
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

        for lic in licenses:
            cdx_license = CycloneDxLicense(name=lic.name, id=lic.spdx_id)

            component.licenses.add(cdx_license)
            if component.evidence:
                component.evidence.licenses.add(cdx_license.bom_ref)

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
