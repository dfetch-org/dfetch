"""*Dfetch* can generate a software Bill-of-Materials (SBOM).

An SBOM lists the components and their supply chain relationships. Downstream
users of the software can assess the licenses used and potential risk of dependencies.

The generated SBOM can be used as input for other tools to monitor dependencies.
The tools track vulnerabilities or can enforce a license policy within an organization.

See https://cyclonedx.org/use-cases/ for more details.

*Dfetch* will try to parse the license of each project.  Detected licenses are
recorded as SPDX identifiers.  When a license-like file is present but cannot
be classified, or when no license file is found at all, *dfetch* sets the
``licenses`` field to ``NOASSERTION`` and adds a ``dfetch:license:finding``
property that explains the reason.  This ensures the ``licenses`` field is
never silently omitted and gives downstream compliance tooling actionable
context.

For successfully identified licenses, the raw license file text is embedded
directly in the SBOM:

* ``licenses[].text`` — the license file content, base64-encoded, with
  ``contentType: text/plain`` and ``encoding: base64``.  Downstream tooling
  can decode and verify the text against the declared SPDX identifier without
  fetching the source tree again.

For NOASSERTION cases, additional enhancements are provided:

* ``licenses[].acknowledgement`` — set to ``CONCLUDED`` to indicate the license
  assertion was determined by analysis.
* ``licenses[].text`` — contains a human-readable explanation of why
  NOASSERTION was set.
* ``dfetch:license:noassertion:reason`` — a machine-readable enum-style value
  indicating the specific reason (``NO_LICENSE_FILE`` or
  ``UNCLASSIFIABLE_LICENSE_TEXT``).

For every scanned component, three additional properties are recorded:

* ``dfetch:license:<spdx-id>:confidence`` — the probability score returned by
  *infer-license* for each identified license (only present when a license is
  successfully identified).
* ``dfetch:license:threshold`` — the minimum confidence required to accept an
  inference (``0.80`` by default).  Auditors can use this to understand under
  what conditions a license was accepted or rejected.
* ``dfetch:license:tool`` — the *infer-license* library version used during the
  scan, enabling reproducible re-evaluation as the library evolves.

.. scenario-include:: ../features/report-sbom.feature
   :scenario:
        A fetched project generates a json sbom

.. scenario-include:: ../features/report-sbom-license.feature
   :scenario:
        A fetched archive with an identified license embeds base64 license text

.. scenario-include:: ../features/report-sbom-license.feature
   :scenario:
        A fetched archive with an unclassifiable license file gets NOASSERTION

.. scenario-include:: ../features/report-sbom-license.feature
   :scenario:
        A fetched archive with no license file gets NOASSERTION

Archive dependencies
--------------------
Archive dependencies (tar.gz, zip, …) are recorded with a ``distribution``
external reference and, when an ``integrity.hash:`` field is set, a ``SHA-256``
component hash for supply-chain integrity verification.

.. scenario-include:: ../features/report-sbom-archive.feature
   :scenario:
        A fetched archive without a hash generates a json sbom

.. scenario-include:: ../features/report-sbom-archive.feature
   :scenario:
        A fetched archive with sha256 hash generates a json sbom with hash

Gitlab
------
Let *DFetch* generate a SBoM and add the result as artifact in your gitlab-ci runner.
See `gitlab dependency scanning`_ for more information.

.. code-block:: yaml

    dfetch:
      image: "python:3.13"
      script:
      - pip install dfetch
      - dfetch report -t sbom -o dfetch.cdx.json
      artifacts:
        reports:
          cyclonedx:
            - dfetch.cdx.json

.. _`gitlab dependency scanning`:
     https://docs.gitlab.com/user/application_security/dependency_scanning/dependency_scanning_sbom/#cyclonedx-software-bill-of-materials

Github
------

A SBoM report can be generated in a github action as such:

.. code-block:: yaml

    jobs:
      SBOM-generation:

        runs-on: ubuntu-latest

        steps:
        - uses: actions/checkout@v5
        - uses: actions/setup-python@v6
          with:
            python-version: '3.13'
        - name: Install dfetch from GitHub
          run: pip install git+https://github.com/dfetch-org/dfetch.git@main#egg=dfetch
          shell: bash
        - name: Generate SBOM with dfetch
          run: dfetch report -t sbom -o dfetch.cdx.json
          shell: bash
        - uses: actions/upload-artifact@v4
          with:
            name: sbom
            path: dfetch.cdx.json

For more information see the `Github dependency submission`_.

.. _`Github dependency submission`:
     https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/using-the-dependency-submission-api
"""

import base64
from decimal import Decimal
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version

from cyclonedx.builder.this import this_component as cdx_lib_component
from cyclonedx.model import (
    AttachedText,
    Encoding,
    ExternalReference,
    ExternalReferenceType,
    HashAlgorithm,
    HashType,
    Property,
    XsUri,
)
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
from cyclonedx.model.license import LicenseAcknowledgement
from cyclonedx.output import make_outputter
from cyclonedx.schema import OutputFormat, SchemaVersion
from packageurl import PackageURL

import dfetch
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.reporter import Reporter
from dfetch.util.license import License as DfetchLicense
from dfetch.util.license import LicenseScanResult
from dfetch.util.purl import vcs_url_to_purl
from dfetch.vcs.archive import archive_url_to_purl, is_archive_url
from dfetch.vcs.integrity_hash import IntegrityHash

# PyRight is pedantic with decorators see https://github.com/madpah/serializable/issues/8
# It might be fixable with https://github.com/microsoft/pyright/discussions/4426, would prefer
# upstream fix, for now suppress, mypy will keep us safe.
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false


#: Version of the *infer-license* library used for license text analysis.
try:
    INFER_LICENSE_VERSION: str = pkg_version("infer-license")
except PackageNotFoundError:
    INFER_LICENSE_VERSION = "unknown"

# Map from dfetch hash-field algorithm prefix to CycloneDX HashAlgorithm name
DFETCH_TO_CDX_HASH_ALGORITHM: dict[str, str] = {
    "sha256": "SHA-256",
    "sha384": "SHA-384",
    "sha512": "SHA-512",
}


def _make_license_text_attachment(text: str) -> AttachedText:
    """Return *text* as a base64-encoded ``AttachedText`` ready for CycloneDX."""
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return AttachedText(
        content=encoded, content_type="text/plain", encoding=Encoding.BASE_64
    )


class SbomReporter(Reporter):
    """Reporter for generating SBoM's."""

    dfetch_tool = Component(
        type=ComponentType.APPLICATION,
        supplier=OrganizationalEntity(name="dfetch-org"),
        name="dfetch",
        version=dfetch.__version__,
        bom_ref=f"dfetch-{dfetch.__version__}",
        licenses=[
            CycloneDxLicense(id="MIT", acknowledgement=LicenseAcknowledgement.DECLARED)
        ],
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

    def __init__(self, manifest: Manifest) -> None:
        """Start the report."""
        super().__init__(manifest)
        self._bom = Bom()
        self._bom.metadata.tools.components.add(self.dfetch_tool)
        self._bom.metadata.tools.components.add(cdx_lib_component())

    def add_project(
        self,
        project: ProjectEntry,
        license_scan: LicenseScanResult,
        version: str,
    ) -> None:
        """Add a project to the report."""
        subpath = project.source or None
        if project.vcs == "archive" or is_archive_url(project.remote_url):
            purl = archive_url_to_purl(
                project.remote_url, version=version, subpath=subpath
            )
        else:
            purl = vcs_url_to_purl(project.remote_url, version=version, subpath=subpath)
        name = project.name if purl.type == "generic" else purl.name
        version = purl.version or version
        location = self.manifest.find_name_in_manifest(project.name)
        component = Component(
            name=name,
            version=version,
            bom_ref=f"{project.name}-{version}",
            type=ComponentType.LIBRARY,
            purl=purl,
            evidence=ComponentEvidence(
                occurrences=[
                    Occurrence(
                        location=self.manifest.relative_path,
                        line=location.line_number,
                        offset=location.start,
                    )
                ],
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
                        concluded_value=name,
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
                                value=f"Determined from {project.remote_url} as used"
                                f" for the project {project.name} in dfetch.yaml",
                            )
                        ],
                        concluded_value=purl.to_string(),
                    ),
                ],
            ),
        )
        self._apply_external_references(component, purl, version)
        self._apply_licenses(component, license_scan)
        self._bom.components.add(component)

    @staticmethod
    def _apply_external_references(
        component: Component, purl: PackageURL, version: str
    ) -> None:
        """Attach external references to *component* based on its PURL type."""
        if purl.type == "github":
            component.group = purl.namespace
            component.external_references.add(
                ExternalReference(
                    type=ExternalReferenceType.VCS,
                    url=XsUri(f"https://github.com/{purl.namespace}/{purl.name}"),
                )
            )
        elif purl.type == "bitbucket":
            component.group = purl.namespace
            component.external_references.add(
                ExternalReference(
                    type=ExternalReferenceType.VCS,
                    url=XsUri(f"https://bitbucket.org/{purl.namespace}/{purl.name}"),
                )
            )
        elif purl.qualifiers.get("download_url"):
            SbomReporter._apply_archive_refs(component, purl, version)
        else:
            SbomReporter._apply_vcs_refs(component, purl)

    @staticmethod
    def _apply_archive_refs(
        component: Component, purl: PackageURL, version: str
    ) -> None:
        """Add DISTRIBUTION reference and optional hash for an archive dependency."""
        download_url = purl.qualifiers["download_url"]
        component.group = purl.namespace or None  # type: ignore[assignment]
        component.external_references.add(
            ExternalReference(
                type=ExternalReferenceType.DISTRIBUTION,
                url=XsUri(download_url),
            )
        )
        integrity = IntegrityHash.parse(version) if version else None
        if integrity:
            cdx_algo_name = DFETCH_TO_CDX_HASH_ALGORITHM.get(integrity.algorithm)
            if cdx_algo_name:
                component.hashes.add(
                    HashType(
                        alg=HashAlgorithm(cdx_algo_name),
                        content=integrity.hex_digest,
                    )
                )

    @staticmethod
    def _apply_vcs_refs(component: Component, purl: PackageURL) -> None:
        """Add VCS external reference and group for a generic VCS dependency."""
        component.group = purl.namespace or None
        vcs_url = purl.qualifiers.get("vcs_url", "")
        # ExternalReferenceType.VCS does not support ssh:// urls
        if vcs_url and "ssh://" not in vcs_url:
            component.external_references.add(
                ExternalReference(
                    type=ExternalReferenceType.VCS,
                    url=XsUri(vcs_url),
                )
            )

    @staticmethod
    def _build_cdx_license(lic: DfetchLicense) -> CycloneDxLicense:
        """Build a CycloneDX license entry, embedding base64 text when available."""
        text_attachment = _make_license_text_attachment(lic.text) if lic.text else None
        if lic.spdx_id:
            return CycloneDxLicense(id=lic.spdx_id, text=text_attachment)
        return CycloneDxLicense(name=lic.name, text=text_attachment)

    @staticmethod
    def _attach_identified_licenses(
        component: Component, identified: list[DfetchLicense]
    ) -> None:
        """Add each identified license to *component* and record its confidence."""
        for lic in identified:
            cdx_license = SbomReporter._build_cdx_license(lic)
            component.licenses.add(cdx_license)
            if component.evidence:
                component.evidence.licenses.add(cdx_license)
            label = lic.spdx_id or lic.name or "unknown"
            component.properties.add(
                Property(
                    name=f"dfetch:license:{label}:confidence",
                    value=f"{lic.probability:.2f}",
                )
            )

    @staticmethod
    def _apply_licenses(component: Component, license_scan: LicenseScanResult) -> None:
        """Attach license information to *component* and its evidence block.

        Three cases are handled:

        * Project was not fetched → nothing is added (no assertion possible).
        * License files were found and identified → SPDX identifiers are
          attached together with the base64-encoded license text, and
          per-license confidence scores are recorded.
        * License files were found but unclassified, **or** no license file was
          found at all → ``NOASSERTION`` is set with enhanced metadata:
          - ``acknowledgement`` set to ``CONCLUDED``
          - ``text`` contains a human-readable explanation
          - ``dfetch:license:noassertion:reason`` property with machine-readable
            enum value (``NO_LICENSE_FILE`` or ``UNCLASSIFIABLE_LICENSE_TEXT``)
          - ``dfetch:license:finding`` property records the reason for downstream
            compliance tooling.

        In all scanned cases, ``dfetch:license:threshold`` and
        ``dfetch:license:tool`` properties are added so auditors can reproduce
        or re-evaluate results if the threshold changes.
        """
        if not license_scan.was_scanned:
            return

        # Always record the detection tool and threshold used during this scan
        # so downstream consumers can reproduce or re-evaluate the results.
        component.properties.add(
            Property(
                name="dfetch:license:tool",
                value=f"infer-license {INFER_LICENSE_VERSION}",
            )
        )
        component.properties.add(
            Property(
                name="dfetch:license:threshold",
                value=f"{license_scan.threshold:.2f}",
            )
        )

        if license_scan.identified:
            SbomReporter._attach_identified_licenses(component, license_scan.identified)
        else:
            if license_scan.unclassified_files:
                files_str = ", ".join(sorted(license_scan.unclassified_files))
                acknowledgement_text = (
                    f"License file(s) found ({files_str}) but could not be classified"
                )
                reason = "UNCLASSIFIABLE_LICENSE_TEXT"
            else:
                acknowledgement_text = "No license file found in source tree"
                reason = "NO_LICENSE_FILE"

            noassertion = CycloneDxLicense(
                id="NOASSERTION",
                acknowledgement=LicenseAcknowledgement.CONCLUDED,
                text=AttachedText(
                    content=acknowledgement_text,
                    content_type="text/plain",
                ),
            )
            component.licenses.add(noassertion)
            if component.evidence:
                component.evidence.licenses.add(noassertion)

            component.properties.add(
                Property(
                    name="dfetch:license:noassertion:reason",
                    value=reason,
                )
            )

        if license_scan.unclassified_files:
            files_str = ", ".join(sorted(license_scan.unclassified_files))
            component.properties.add(
                Property(
                    name="dfetch:license:finding",
                    value=f"License file(s) found ({files_str}) but could not be classified",
                )
            )
        elif not license_scan.identified:
            component.properties.add(
                Property(
                    name="dfetch:license:finding",
                    value="No license file found in source tree",
                )
            )

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
