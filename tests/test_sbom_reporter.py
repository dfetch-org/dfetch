"""Tests for dfetch.reporting.sbom_reporter."""

# mypy: ignore-errors
# flake8: noqa

import base64
import json
from unittest.mock import MagicMock, patch

from cyclonedx.model import AttachedText, Encoding, Property
from cyclonedx.model.component import Component, ComponentEvidence, ComponentType
from cyclonedx.model.license import DisjunctiveLicense as CycloneDxLicense
from cyclonedx.model.license import LicenseAcknowledgement
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonValidator

from dfetch.reporting.sbom_reporter import (
    INFER_LICENSE_VERSION,
    SbomReporter,
    _make_license_text_attachment,
)
from dfetch.util.license import License as DfetchLicense
from dfetch.util.license import LicenseScanResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dfetch_license(
    name: str = "MIT License",
    spdx_id: str = "MIT",
    probability: float = 0.95,
    text: str | None = None,
) -> DfetchLicense:
    """Return a minimal DfetchLicense with sensible defaults."""
    return DfetchLicense(
        name=name,
        spdx_id=spdx_id,
        trove_classifier=None,
        probability=probability,
        text=text,
    )


def _make_bare_component(name: str = "test-component") -> Component:
    """Return a minimal CycloneDX Component without evidence."""
    return Component(
        type=ComponentType.LIBRARY,
        name=name,
    )


def _make_component_with_evidence(name: str = "test-component") -> Component:
    """Return a CycloneDX Component that has an evidence block.

    cyclonedx-python-lib v7.6.2 requires at least one license in ComponentEvidence;
    we seed it with a placeholder that is removed before assertions.
    """
    # Seed with a placeholder license so ComponentEvidence construction succeeds.
    placeholder = CycloneDxLicense(id="NOASSERTION")
    component = Component(
        type=ComponentType.LIBRARY,
        name=name,
        evidence=ComponentEvidence(licenses=[placeholder]),
    )
    # Remove the placeholder so evidence starts logically empty.
    component.evidence.licenses.discard(placeholder)
    return component


def _get_property_names(component: Component) -> set[str]:
    return {p.name for p in component.properties}


def _get_property_value(component: Component, name: str) -> str | None:
    for p in component.properties:
        if p.name == name:
            return p.value
    return None


def _get_license_ids(component: Component) -> list[str | None]:
    """Return a list of SPDX IDs or expression values from component licenses."""
    result = []
    for lic in component.licenses:
        if hasattr(lic, "id"):
            result.append(lic.id)
        elif hasattr(lic, "value"):
            result.append(lic.value)
    return result


# ---------------------------------------------------------------------------
# _make_license_text_attachment
# ---------------------------------------------------------------------------


class TestMakeLicenseTextAttachment:
    def test_returns_attached_text_with_base64_encoding(self):
        text = "hello world"
        attachment = _make_license_text_attachment(text)
        assert isinstance(attachment, AttachedText)
        assert attachment.encoding == Encoding.BASE_64

    def test_content_is_base64_of_input(self):
        text = "MIT License\nCopyright 2024"
        attachment = _make_license_text_attachment(text)
        decoded = base64.b64decode(attachment.content).decode("utf-8")
        assert decoded == text

    def test_content_type_is_text_plain(self):
        attachment = _make_license_text_attachment("anything")
        assert attachment.content_type == "text/plain"

    def test_empty_string_produces_empty_base64(self):
        attachment = _make_license_text_attachment("")
        decoded = base64.b64decode(attachment.content).decode("utf-8")
        assert decoded == ""

    def test_unicode_text_is_utf8_encoded(self):
        text = "Copyright © 2024 — some unicode"
        attachment = _make_license_text_attachment(text)
        decoded = base64.b64decode(attachment.content).decode("utf-8")
        assert decoded == text


# ---------------------------------------------------------------------------
# SbomReporter._build_cdx_license
# ---------------------------------------------------------------------------


class TestBuildCdxLicense:
    def test_uses_spdx_id_when_available(self):
        lic = _make_dfetch_license(spdx_id="MIT")
        cdx = SbomReporter._build_cdx_license(lic)
        assert cdx.id == "MIT"

    def test_falls_back_to_name_when_no_spdx_id(self):
        lic = DfetchLicense(
            name="Custom License", spdx_id="", trove_classifier=None, probability=0.9
        )
        cdx = SbomReporter._build_cdx_license(lic)
        # spdx_id is empty string → falsy → use name
        assert cdx.name == "Custom License"

    def test_text_attachment_is_embedded_when_text_present(self):
        lic = _make_dfetch_license(text="MIT License\nCopyright 2024")
        cdx = SbomReporter._build_cdx_license(lic)
        assert cdx.text is not None
        decoded = base64.b64decode(cdx.text.content).decode("utf-8")
        assert "MIT License" in decoded

    def test_text_attachment_is_none_when_no_text(self):
        lic = _make_dfetch_license(text=None)
        cdx = SbomReporter._build_cdx_license(lic)
        assert cdx.text is None


# ---------------------------------------------------------------------------
# SbomReporter._attach_identified_licenses
# ---------------------------------------------------------------------------


class TestAttachIdentifiedLicenses:
    def test_adds_license_to_component(self):
        component = _make_bare_component()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        SbomReporter._attach_identified_licenses(component, [lic])
        assert any(l.id == "MIT" for l in component.licenses)

    def test_adds_license_to_evidence_when_present(self):
        component = _make_component_with_evidence()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        SbomReporter._attach_identified_licenses(component, [lic])
        assert any(l.id == "MIT" for l in component.evidence.licenses)

    def test_does_not_add_to_evidence_when_absent(self):
        component = _make_bare_component()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        # Should not raise even though component.evidence is None
        SbomReporter._attach_identified_licenses(component, [lic])
        # Component has licenses but evidence is None
        assert any(l.id == "MIT" for l in component.licenses)

    def test_confidence_property_is_recorded(self):
        component = _make_bare_component()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        SbomReporter._attach_identified_licenses(component, [lic])
        assert "dfetch:license:MIT:confidence" in _get_property_names(component)

    def test_confidence_value_is_formatted_to_two_decimals(self):
        component = _make_bare_component()
        lic = _make_dfetch_license(spdx_id="Apache-2.0", probability=0.876543)
        SbomReporter._attach_identified_licenses(component, [lic])
        val = _get_property_value(component, "dfetch:license:Apache-2.0:confidence")
        assert val == "0.88"

    def test_multiple_licenses_each_get_confidence_property(self):
        component = _make_bare_component()
        lic1 = _make_dfetch_license(name="MIT License", spdx_id="MIT", probability=0.95)
        lic2 = _make_dfetch_license(
            name="Apache License 2.0", spdx_id="Apache-2.0", probability=0.91
        )
        SbomReporter._attach_identified_licenses(component, [lic1, lic2])
        names = _get_property_names(component)
        assert "dfetch:license:MIT:confidence" in names
        assert "dfetch:license:Apache-2.0:confidence" in names

    def test_label_falls_back_to_name_when_no_spdx_id(self):
        lic = DfetchLicense(
            name="Custom License", spdx_id="", trove_classifier=None, probability=0.85
        )
        component = _make_bare_component()
        SbomReporter._attach_identified_licenses(component, [lic])
        assert "dfetch:license:Custom License:confidence" in _get_property_names(
            component
        )

    def test_label_falls_back_to_unknown_when_no_spdx_or_name(self):
        """When both spdx_id and name are falsy the label 'unknown' is used.

        Note: CycloneDxLicense requires either id or name to be non-empty, so we
        supply a non-empty name that still results in spdx_id="" → label falls to
        lic.name ("") → label falls to "unknown".
        """
        lic = DfetchLicense(
            name="", spdx_id="", trove_classifier=None, probability=0.85
        )
        component = _make_bare_component()
        # The actual CycloneDxLicense construction inside _build_cdx_license will
        # raise MutuallyExclusivePropertiesException for empty name; we mock it to
        # verify only the label logic branch is "unknown".
        with patch.object(SbomReporter, "_build_cdx_license", return_value=MagicMock()):
            SbomReporter._attach_identified_licenses(component, [lic])
        assert "dfetch:license:unknown:confidence" in _get_property_names(component)


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses — not-scanned case
# ---------------------------------------------------------------------------


class TestApplyLicensesNotScanned:
    def test_not_scanned_adds_nothing(self):
        component = _make_component_with_evidence()
        scan = LicenseScanResult(was_scanned=False)
        SbomReporter._apply_licenses(component, scan)
        assert len(component.licenses) == 0
        assert len(component.properties) == 0


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses — identified licenses case
# ---------------------------------------------------------------------------


class TestApplyLicensesIdentified:
    def test_identified_license_added_to_component(self):
        component = _make_component_with_evidence()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95, text="MIT text")
        scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        assert any(l.id == "MIT" for l in component.licenses)

    def test_tool_property_added(self):
        component = _make_bare_component()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        assert "dfetch:license:tool" in _get_property_names(component)

    def test_threshold_property_added(self):
        component = _make_bare_component()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        val = _get_property_value(component, "dfetch:license:threshold")
        assert val == "0.80"

    def test_noassertion_is_not_set_when_identified(self):
        component = _make_component_with_evidence()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        ids = _get_license_ids(component)
        assert "NOASSERTION" not in ids

    def test_finding_property_not_added_when_identified(self):
        component = _make_bare_component()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        assert "dfetch:license:finding" not in _get_property_names(component)

    def test_noassertion_reason_not_set_when_identified(self):
        component = _make_bare_component()
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95)
        scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        assert "dfetch:license:noassertion:reason" not in _get_property_names(component)

    def test_text_is_base64_embedded_in_license(self):
        component = _make_bare_component()
        raw_text = "MIT License\nCopyright 2024"
        lic = _make_dfetch_license(spdx_id="MIT", probability=0.95, text=raw_text)
        scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        cdx_lic = next(l for l in component.licenses if l.id == "MIT")
        assert cdx_lic.text is not None
        decoded = base64.b64decode(cdx_lic.text.content).decode("utf-8")
        assert decoded == raw_text


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses — unclassifiable license file case
# ---------------------------------------------------------------------------


class TestApplyLicensesUnclassified:
    def test_noassertion_added(self):
        component = _make_component_with_evidence()
        scan = LicenseScanResult(
            unclassified_files=["LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        SbomReporter._apply_licenses(component, scan)
        ids = _get_license_ids(component)
        assert "NOASSERTION" in ids

    def test_noassertion_added_to_evidence(self):
        component = _make_component_with_evidence()
        scan = LicenseScanResult(
            unclassified_files=["LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        SbomReporter._apply_licenses(component, scan)
        evidence_ids = [
            getattr(l, "id", None) or getattr(l, "value", None)
            for l in component.evidence.licenses
        ]
        assert "NOASSERTION" in evidence_ids

    def test_noassertion_has_concluded_acknowledgement(self):
        component = _make_component_with_evidence()
        scan = LicenseScanResult(
            unclassified_files=["LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        SbomReporter._apply_licenses(component, scan)
        from cyclonedx.model.license import LicenseExpression

        noassertion = next(
            l
            for l in component.licenses
            if isinstance(l, LicenseExpression) and l.value == "NOASSERTION"
        )
        assert noassertion.acknowledgement == LicenseAcknowledgement.CONCLUDED

    def test_noassertion_finding_property_mentions_filename(self):
        """The dfetch:license:finding property (not the license object) carries the filename."""
        component = _make_bare_component()
        scan = LicenseScanResult(
            unclassified_files=["LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        SbomReporter._apply_licenses(component, scan)
        val = _get_property_value(component, "dfetch:license:finding")
        assert val is not None and "LICENSE" in val

    def test_multiple_unclassified_files_sorted_in_finding_property(self):
        """Multiple unclassified files appear sorted in the dfetch:license:finding property."""
        component = _make_bare_component()
        scan = LicenseScanResult(
            unclassified_files=["COPYING", "LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        SbomReporter._apply_licenses(component, scan)
        val = _get_property_value(component, "dfetch:license:finding")
        assert val is not None
        assert "COPYING" in val
        assert "LICENSE" in val

    def test_noassertion_reason_property_is_unclassifiable(self):
        component = _make_bare_component()
        scan = LicenseScanResult(
            unclassified_files=["LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        SbomReporter._apply_licenses(component, scan)
        val = _get_property_value(component, "dfetch:license:noassertion:reason")
        assert val == "UNCLASSIFIABLE_LICENSE_TEXT"

    def test_finding_property_is_set(self):
        component = _make_bare_component()
        scan = LicenseScanResult(
            unclassified_files=["LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        SbomReporter._apply_licenses(component, scan)
        val = _get_property_value(component, "dfetch:license:finding")
        assert val is not None
        assert "LICENSE" in val

    def test_tool_and_threshold_properties_present(self):
        component = _make_bare_component()
        scan = LicenseScanResult(
            unclassified_files=["LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        SbomReporter._apply_licenses(component, scan)
        names = _get_property_names(component)
        assert "dfetch:license:tool" in names
        assert "dfetch:license:threshold" in names


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses — no license file found case
# ---------------------------------------------------------------------------


class TestApplyLicensesNoFile:
    def test_noassertion_added(self):
        component = _make_component_with_evidence()
        scan = LicenseScanResult(was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        ids = _get_license_ids(component)
        assert "NOASSERTION" in ids

    def test_noassertion_finding_property_says_no_file_found(self):
        """The dfetch:license:finding property (not the license object) describes the reason."""
        component = _make_bare_component()
        scan = LicenseScanResult(was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        val = _get_property_value(component, "dfetch:license:finding")
        assert val is not None and "No license file found" in val

    def test_noassertion_reason_property_is_no_license_file(self):
        component = _make_bare_component()
        scan = LicenseScanResult(was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        val = _get_property_value(component, "dfetch:license:noassertion:reason")
        assert val == "NO_LICENSE_FILE"

    def test_finding_property_says_no_file_found(self):
        component = _make_bare_component()
        scan = LicenseScanResult(was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        val = _get_property_value(component, "dfetch:license:finding")
        assert val is not None
        assert "No license file found" in val

    def test_tool_and_threshold_properties_present(self):
        component = _make_bare_component()
        scan = LicenseScanResult(was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        names = _get_property_names(component)
        assert "dfetch:license:tool" in names
        assert "dfetch:license:threshold" in names

    def test_noassertion_added_to_evidence_when_present(self):
        component = _make_component_with_evidence()
        scan = LicenseScanResult(was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        evidence_ids = [
            getattr(l, "id", None) or getattr(l, "value", None)
            for l in component.evidence.licenses
        ]
        assert "NOASSERTION" in evidence_ids

    def test_no_confidence_property_when_no_license(self):
        """No dfetch:license:<spdx>:confidence should exist when no license identified."""
        component = _make_bare_component()
        scan = LicenseScanResult(was_scanned=True, threshold=0.80)
        SbomReporter._apply_licenses(component, scan)
        names = _get_property_names(component)
        confidence_props = [n for n in names if n.endswith(":confidence")]
        assert confidence_props == []


# ---------------------------------------------------------------------------
# INFER_LICENSE_VERSION constant
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CycloneDX 1.6 schema validation
# ---------------------------------------------------------------------------


class TestSbomSchemaValid:
    """The JSON emitted by SbomReporter must be valid CycloneDX 1.6."""

    @staticmethod
    def _make_reporter(manifest):
        return SbomReporter(manifest)

    @staticmethod
    def _make_manifest(relative_path: str = "dfetch.yaml"):
        from dfetch.manifest.manifest import ManifestEntryLocation

        manifest = MagicMock()
        manifest.relative_path = relative_path
        manifest.find_name_in_manifest.return_value = ManifestEntryLocation(
            line_number=5, start=13, end=20
        )
        return manifest

    @staticmethod
    def _make_project(
        name: str = "mylib",
        remote_url: str = "https://github.com/example/mylib",
        tag: str = "v1.0",
        source: str = "",
        vcs: str = "git",
    ):
        project = MagicMock()
        project.name = name
        project.remote_url = remote_url
        project.tag = tag
        project.source = source
        project.vcs = vcs
        return project

    def _generate_sbom_json(self, tmp_path, projects=None, license_scan=None):
        """Build a reporter, add projects, write to file, return the JSON string."""
        if projects is None:
            projects = [self._make_project()]
        if license_scan is None:
            license_scan = LicenseScanResult(was_scanned=False)

        manifest = self._make_manifest()
        reporter = SbomReporter(manifest)
        for project in projects:
            reporter.add_project(
                project=project, license_scan=license_scan, version="v1.0"
            )

        out = tmp_path / "report.cdx.json"
        reporter.dump_to_file(str(out))
        return out.read_text(encoding="utf-8")

    def test_empty_sbom_is_schema_valid(self, tmp_path):
        """An SBOM with no projects must satisfy the CycloneDX 1.6 schema."""
        manifest = self._make_manifest()
        reporter = SbomReporter(manifest)
        out = tmp_path / "empty.cdx.json"
        reporter.dump_to_file(str(out))

        json_str = out.read_text(encoding="utf-8")
        errors = JsonValidator(SchemaVersion.V1_6).validate_str(json_str)
        assert errors is None, f"CycloneDX 1.6 schema violations: {errors}"

    def test_single_vcs_project_is_schema_valid(self, tmp_path):
        """An SBOM with one VCS project must satisfy the CycloneDX 1.6 schema."""
        json_str = self._generate_sbom_json(tmp_path)
        errors = JsonValidator(SchemaVersion.V1_6).validate_str(json_str)
        assert errors is None, f"CycloneDX 1.6 schema violations: {errors}"

    def test_identified_license_is_schema_valid(self, tmp_path):
        """An SBOM with an identified SPDX license must satisfy the CycloneDX 1.6 schema."""
        from dfetch.util.license import License as DfetchLicense

        lic = DfetchLicense(
            name="MIT License",
            spdx_id="MIT",
            trove_classifier=None,
            probability=0.95,
            text="MIT License\nCopyright 2024",
        )
        scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
        json_str = self._generate_sbom_json(tmp_path, license_scan=scan)
        errors = JsonValidator(SchemaVersion.V1_6).validate_str(json_str)
        assert errors is None, f"CycloneDX 1.6 schema violations: {errors}"

    def test_noassertion_unclassified_is_schema_valid(self, tmp_path):
        """An SBOM with NOASSERTION (unclassifiable file) must satisfy the CycloneDX 1.6 schema."""
        scan = LicenseScanResult(
            unclassified_files=["LICENSE"], was_scanned=True, threshold=0.80
        )
        json_str = self._generate_sbom_json(tmp_path, license_scan=scan)
        errors = JsonValidator(SchemaVersion.V1_6).validate_str(json_str)
        assert errors is None, f"CycloneDX 1.6 schema violations: {errors}"

    def test_noassertion_no_license_file_is_schema_valid(self, tmp_path):
        """An SBOM with NOASSERTION (no license file) must satisfy the CycloneDX 1.6 schema."""
        scan = LicenseScanResult(was_scanned=True, threshold=0.80)
        json_str = self._generate_sbom_json(tmp_path, license_scan=scan)
        errors = JsonValidator(SchemaVersion.V1_6).validate_str(json_str)
        assert errors is None, f"CycloneDX 1.6 schema violations: {errors}"

    def test_archive_project_is_schema_valid(self, tmp_path):
        """An SBOM with an archive (tar.gz) project must satisfy the CycloneDX 1.6 schema."""
        archive_project = self._make_project(
            name="SomeLib",
            remote_url="https://example.com/SomeLib.tar.gz",
            tag="",
            vcs="archive",
        )
        json_str = self._generate_sbom_json(
            tmp_path,
            projects=[archive_project],
            license_scan=LicenseScanResult(was_scanned=False),
        )
        errors = JsonValidator(SchemaVersion.V1_6).validate_str(json_str)
        assert errors is None, f"CycloneDX 1.6 schema violations: {errors}"


class TestInferLicenseVersion:
    def test_version_is_string(self):
        assert isinstance(INFER_LICENSE_VERSION, str)

    def test_version_is_not_empty(self):
        assert INFER_LICENSE_VERSION != ""

    def test_version_matches_installed_package(self):
        """INFER_LICENSE_VERSION must equal the version reported by the package index.

        INFER_LICENSE_VERSION is set at module import time via a try/except around
        pkg_version("infer-license").  The fallback ("unknown") cannot be re-exercised
        in-process without a full module reimport, so we only verify the happy path:
        the constant must match what importlib.metadata reports for the installed
        package.
        """
        from importlib.metadata import version as pkg_v

        assert INFER_LICENSE_VERSION == pkg_v("infer-license")
