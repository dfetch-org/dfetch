"""Tests for dfetch.reporting.sbom_reporter (PR #1112 license changes)."""

# mypy: ignore-errors
# flake8: noqa

import base64
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from cyclonedx.model import AttachedText, Encoding, Property
from cyclonedx.model.component import Component, ComponentEvidence, ComponentType
from cyclonedx.model.license import DisjunctiveLicense as CycloneDxLicense
from cyclonedx.model.license import LicenseAcknowledgement

from dfetch.reporting.sbom_reporter import (
    INFER_LICENSE_VERSION,
    SbomReporter,
    _make_license_text_attachment,
)
from dfetch.util.license import License as DfetchLicense
from dfetch.util.license import LicenseScanResult


# ---------------------------------------------------------------------------
# Helper – create a minimal Component with an evidence block
# ---------------------------------------------------------------------------


def _make_component(name: str = "test-component") -> Component:
    """Return a minimal CycloneDX Component with a ComponentEvidence block."""
    comp = Component(
        name=name,
        version="1.0",
        type=ComponentType.LIBRARY,
        evidence=ComponentEvidence(),
    )
    return comp


def _get_property_names(component: Component) -> set:
    return {p.name for p in component.properties}


def _get_property_value(component: Component, name: str) -> str | None:
    for p in component.properties:
        if p.name == name:
            return p.value
    return None


def _get_license_ids(license_set) -> set:
    """Extract the id/name strings from a set of CycloneDxLicense objects."""
    ids = set()
    for lic in license_set:
        if hasattr(lic, "id") and lic.id:
            ids.add(lic.id)
        elif hasattr(lic, "name") and lic.name:
            ids.add(lic.name)
    return ids


# ---------------------------------------------------------------------------
# _make_license_text_attachment
# ---------------------------------------------------------------------------


def test_make_license_text_attachment_returns_base64():
    text = "MIT License\n\nCopyright (c) 2024 Test"
    attachment = _make_license_text_attachment(text)

    assert attachment.encoding == Encoding.BASE_64
    expected_encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    assert attachment.content == expected_encoded


def test_make_license_text_attachment_content_type():
    attachment = _make_license_text_attachment("some license text")
    assert attachment.content_type == "text/plain"


def test_make_license_text_attachment_roundtrip():
    original_text = "Apache License\n\nVersion 2.0"
    attachment = _make_license_text_attachment(original_text)
    decoded = base64.b64decode(attachment.content).decode("utf-8")
    assert decoded == original_text


def test_make_license_text_attachment_empty_string():
    attachment = _make_license_text_attachment("")
    assert attachment.content == ""


def test_make_license_text_attachment_unicode():
    text = "Licença MIT\nCopyright © 2024"
    attachment = _make_license_text_attachment(text)
    decoded = base64.b64decode(attachment.content).decode("utf-8")
    assert decoded == text


# ---------------------------------------------------------------------------
# SbomReporter._build_cdx_license
# ---------------------------------------------------------------------------


def test_build_cdx_license_with_spdx_id():
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    cdx = SbomReporter._build_cdx_license(lic)
    assert cdx.id == "MIT"
    assert cdx.text is None


def test_build_cdx_license_with_spdx_id_and_text():
    lic = DfetchLicense(
        name="MIT License",
        spdx_id="MIT",
        trove_classifier=None,
        probability=0.99,
        text="MIT License text here",
    )
    cdx = SbomReporter._build_cdx_license(lic)
    assert cdx.id == "MIT"
    assert cdx.text is not None
    assert cdx.text.encoding == Encoding.BASE_64


def test_build_cdx_license_without_spdx_id_uses_name():
    lic = DfetchLicense(
        name="Custom License",
        spdx_id="",
        trove_classifier=None,
        probability=0.85,
    )
    cdx = SbomReporter._build_cdx_license(lic)
    assert cdx.name == "Custom License"


def test_build_cdx_license_text_is_base64_encoded():
    raw_text = "MIT License\n\nPermission is hereby granted..."
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99, text=raw_text
    )
    cdx = SbomReporter._build_cdx_license(lic)

    expected = base64.b64encode(raw_text.encode("utf-8")).decode("ascii")
    assert cdx.text.content == expected


# ---------------------------------------------------------------------------
# SbomReporter._attach_identified_licenses
# ---------------------------------------------------------------------------


def test_attach_identified_licenses_adds_to_component_licenses():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )

    SbomReporter._attach_identified_licenses(comp, [lic])

    assert any(getattr(l, "id", None) == "MIT" for l in comp.licenses)


def test_attach_identified_licenses_adds_to_evidence():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )

    SbomReporter._attach_identified_licenses(comp, [lic])

    assert comp.evidence is not None
    assert any(getattr(l, "id", None) == "MIT" for l in comp.evidence.licenses)


def test_attach_identified_licenses_records_confidence():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.95
    )

    SbomReporter._attach_identified_licenses(comp, [lic])

    assert "dfetch:license:MIT:confidence" in _get_property_names(comp)
    assert _get_property_value(comp, "dfetch:license:MIT:confidence") == "0.95"


def test_attach_identified_licenses_uses_name_when_no_spdx_id():
    comp = _make_component()
    lic = DfetchLicense(
        name="Custom License",
        spdx_id="",
        trove_classifier=None,
        probability=0.85,
    )

    SbomReporter._attach_identified_licenses(comp, [lic])

    assert "dfetch:license:Custom License:confidence" in _get_property_names(comp)


def test_attach_identified_multiple_licenses():
    comp = _make_component()
    lic1 = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    lic2 = DfetchLicense(
        name="Apache Software License",
        spdx_id="Apache-2.0",
        trove_classifier=None,
        probability=0.92,
    )

    SbomReporter._attach_identified_licenses(comp, [lic1, lic2])

    prop_names = _get_property_names(comp)
    assert "dfetch:license:MIT:confidence" in prop_names
    assert "dfetch:license:Apache-2.0:confidence" in prop_names


def test_attach_identified_licenses_confidence_formatted_two_decimals():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.9
    )

    SbomReporter._attach_identified_licenses(comp, [lic])

    assert _get_property_value(comp, "dfetch:license:MIT:confidence") == "0.90"


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – not scanned
# ---------------------------------------------------------------------------


def test_apply_licenses_not_scanned_adds_nothing():
    comp = _make_component()
    scan = LicenseScanResult(was_scanned=False)

    SbomReporter._apply_licenses(comp, scan)

    assert len(comp.licenses) == 0
    assert len(comp.properties) == 0


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – identified licenses
# ---------------------------------------------------------------------------


def test_apply_licenses_identified_adds_spdx_license():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    assert any(getattr(l, "id", None) == "MIT" for l in comp.licenses)


def test_apply_licenses_identified_records_tool_and_threshold():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    prop_names = _get_property_names(comp)
    assert "dfetch:license:tool" in prop_names
    assert "dfetch:license:threshold" in prop_names


def test_apply_licenses_identified_threshold_value():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    assert _get_property_value(comp, "dfetch:license:threshold") == "0.80"


def test_apply_licenses_identified_no_noassertion():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    ids = _get_license_ids(comp.licenses)
    assert "NOASSERTION" not in ids


def test_apply_licenses_identified_no_finding_property():
    comp = _make_component()
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    assert "dfetch:license:finding" not in _get_property_names(comp)


def test_apply_licenses_identified_embeds_base64_text():
    comp = _make_component()
    raw_text = "MIT License\n\nCopyright (c) 2024"
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99, text=raw_text
    )
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    mit_licenses = [l for l in comp.licenses if getattr(l, "id", None) == "MIT"]
    assert len(mit_licenses) == 1
    assert mit_licenses[0].text is not None
    expected_b64 = base64.b64encode(raw_text.encode("utf-8")).decode("ascii")
    assert mit_licenses[0].text.content == expected_b64


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – unclassified license files
# ---------------------------------------------------------------------------


def test_apply_licenses_unclassified_sets_noassertion():
    comp = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    SbomReporter._apply_licenses(comp, scan)

    ids = _get_license_ids(comp.licenses)
    assert "NOASSERTION" in ids


def test_apply_licenses_unclassified_sets_finding_property():
    comp = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    SbomReporter._apply_licenses(comp, scan)

    finding = _get_property_value(comp, "dfetch:license:finding")
    assert finding is not None
    assert "LICENSE" in finding
    assert "could not be classified" in finding


def test_apply_licenses_unclassified_sets_noassertion_reason():
    comp = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    SbomReporter._apply_licenses(comp, scan)

    reason = _get_property_value(comp, "dfetch:license:noassertion:reason")
    assert reason == "UNCLASSIFIABLE_LICENSE_TEXT"


def test_apply_licenses_unclassified_multiple_files_sorted():
    comp = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["COPYING", "LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    SbomReporter._apply_licenses(comp, scan)

    finding = _get_property_value(comp, "dfetch:license:finding")
    # Files are sorted alphabetically
    assert finding is not None
    assert "COPYING" in finding
    assert "LICENSE" in finding
    # COPYING comes before LICENSE alphabetically
    assert finding.index("COPYING") < finding.index("LICENSE")


def test_apply_licenses_unclassified_records_tool_and_threshold():
    comp = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    SbomReporter._apply_licenses(comp, scan)

    prop_names = _get_property_names(comp)
    assert "dfetch:license:tool" in prop_names
    assert "dfetch:license:threshold" in prop_names


def test_apply_licenses_unclassified_adds_acknowledgement_text():
    comp = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    SbomReporter._apply_licenses(comp, scan)

    noassertion_entries = [
        l for l in comp.licenses if getattr(l, "id", None) == "NOASSERTION"
    ]
    assert len(noassertion_entries) == 1
    assert noassertion_entries[0].text is not None
    assert "could not be classified" in noassertion_entries[0].text.content


def test_apply_licenses_unclassified_evidence_also_has_noassertion():
    comp = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    SbomReporter._apply_licenses(comp, scan)

    assert comp.evidence is not None
    evidence_ids = _get_license_ids(comp.evidence.licenses)
    assert "NOASSERTION" in evidence_ids


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – no license file found
# ---------------------------------------------------------------------------


def test_apply_licenses_no_license_file_sets_noassertion():
    comp = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    ids = _get_license_ids(comp.licenses)
    assert "NOASSERTION" in ids


def test_apply_licenses_no_license_file_sets_finding_property():
    comp = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    finding = _get_property_value(comp, "dfetch:license:finding")
    assert finding == "No license file found in source tree"


def test_apply_licenses_no_license_file_sets_reason_no_license_file():
    comp = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    reason = _get_property_value(comp, "dfetch:license:noassertion:reason")
    assert reason == "NO_LICENSE_FILE"


def test_apply_licenses_no_license_file_explanation_text():
    comp = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    noassertion_entries = [
        l for l in comp.licenses if getattr(l, "id", None) == "NOASSERTION"
    ]
    assert len(noassertion_entries) == 1
    assert noassertion_entries[0].text is not None
    assert noassertion_entries[0].text.content == "No license file found in source tree"


def test_apply_licenses_no_license_file_evidence_has_noassertion():
    comp = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    assert comp.evidence is not None
    evidence_ids = _get_license_ids(comp.evidence.licenses)
    assert "NOASSERTION" in evidence_ids


def test_apply_licenses_no_license_file_records_tool_and_threshold():
    comp = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    prop_names = _get_property_names(comp)
    assert "dfetch:license:tool" in prop_names
    assert "dfetch:license:threshold" in prop_names


# ---------------------------------------------------------------------------
# INFER_LICENSE_VERSION constant
# ---------------------------------------------------------------------------


def test_infer_license_version_is_string():
    assert isinstance(INFER_LICENSE_VERSION, str)
    assert len(INFER_LICENSE_VERSION) > 0


def test_apply_licenses_tool_property_contains_infer_license():
    comp = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)

    SbomReporter._apply_licenses(comp, scan)

    tool_value = _get_property_value(comp, "dfetch:license:tool")
    assert tool_value is not None
    assert "infer-license" in tool_value


# ---------------------------------------------------------------------------
# Edge case – component without evidence block
# ---------------------------------------------------------------------------


def test_apply_licenses_identified_no_evidence_does_not_crash():
    comp = Component(
        name="no-evidence-component",
        version="1.0",
        type=ComponentType.LIBRARY,
    )
    lic = DfetchLicense(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)

    # Should not raise even though component.evidence is None
    SbomReporter._apply_licenses(comp, scan)

    assert any(getattr(l, "id", None) == "MIT" for l in comp.licenses)


def test_apply_licenses_unclassified_no_evidence_does_not_crash():
    comp = Component(
        name="no-evidence-component",
        version="1.0",
        type=ComponentType.LIBRARY,
    )
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    SbomReporter._apply_licenses(comp, scan)

    ids = _get_license_ids(comp.licenses)
    assert "NOASSERTION" in ids