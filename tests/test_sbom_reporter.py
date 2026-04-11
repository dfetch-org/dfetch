"""Unit tests for dfetch.reporting.sbom_reporter – new license handling."""

# mypy: ignore-errors
# flake8: noqa

import base64
from unittest.mock import patch

import pytest

from cyclonedx.model import AttachedText, Encoding, Property
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.license import (
    DisjunctiveLicense as CycloneDxLicense,
    LicenseAcknowledgement,
)

from dfetch.reporting.sbom_reporter import SbomReporter, _make_license_text_attachment
from dfetch.util.license import License as DfetchLicense, LicenseScanResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_license(
    name: str = "MIT License",
    spdx_id: str = "MIT",
    probability: float = 0.95,
    text: str | None = None,
) -> DfetchLicense:
    return DfetchLicense(
        name=name,
        spdx_id=spdx_id,
        trove_classifier=None,
        probability=probability,
        text=text,
    )


def _make_component() -> Component:
    return Component(name="test-component", type=ComponentType.LIBRARY)


def _get_property_names(component: Component) -> list[str]:
    return [p.name for p in component.properties]


def _get_property_value(component: Component, name: str) -> str | None:
    for p in component.properties:
        if p.name == name:
            return p.value
    return None


def _get_license_ids(component: Component) -> list[str]:
    return [lic.id for lic in component.licenses]


# ---------------------------------------------------------------------------
# _make_license_text_attachment
# ---------------------------------------------------------------------------


def test_make_license_text_attachment_base64_encodes_text():
    """The attachment content must be the base64 encoding of the input text."""
    text = "MIT License\nCopyright 2024"
    attachment = _make_license_text_attachment(text)
    expected = base64.b64encode(text.encode("utf-8")).decode("ascii")
    assert attachment.content == expected


def test_make_license_text_attachment_sets_content_type():
    attachment = _make_license_text_attachment("hello")
    assert attachment.content_type == "text/plain"


def test_make_license_text_attachment_sets_encoding():
    attachment = _make_license_text_attachment("hello")
    assert attachment.encoding == Encoding.BASE_64


def test_make_license_text_attachment_empty_string():
    """Empty string encodes to a valid (empty) base64 string."""
    attachment = _make_license_text_attachment("")
    assert attachment.content == base64.b64encode(b"").decode("ascii")


def test_make_license_text_attachment_utf8_content():
    """Non-ASCII text is correctly base64-encoded via UTF-8."""
    text = "Lizenz: Urheberrecht © 2024"
    attachment = _make_license_text_attachment(text)
    expected = base64.b64encode(text.encode("utf-8")).decode("ascii")
    assert attachment.content == expected


# ---------------------------------------------------------------------------
# SbomReporter._build_cdx_license
# ---------------------------------------------------------------------------


def test_build_cdx_license_with_spdx_id():
    """When spdx_id is set it is used as the license id."""
    lic = _make_license(spdx_id="MIT", text=None)
    cdx = SbomReporter._build_cdx_license(lic)
    assert cdx.id == "MIT"


def test_build_cdx_license_with_text_embeds_base64():
    """Text is embedded as a base64 AttachedText when provided."""
    raw = "MIT License\nCopyright 2024"
    lic = _make_license(spdx_id="MIT", text=raw)
    cdx = SbomReporter._build_cdx_license(lic)
    expected_b64 = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    assert cdx.text is not None
    assert cdx.text.content == expected_b64
    assert cdx.text.encoding == Encoding.BASE_64


def test_build_cdx_license_without_text_has_no_attachment():
    """When text is None no text attachment is created."""
    lic = _make_license(spdx_id="MIT", text=None)
    cdx = SbomReporter._build_cdx_license(lic)
    assert cdx.text is None


def test_build_cdx_license_falls_back_to_name_when_no_spdx_id():
    """When spdx_id is empty/None the license name is used."""
    lic = DfetchLicense(
        name="Some Custom License",
        spdx_id="",
        trove_classifier=None,
        probability=0.9,
    )
    cdx = SbomReporter._build_cdx_license(lic)
    assert cdx.id is None
    assert cdx.name == "Some Custom License"


# ---------------------------------------------------------------------------
# SbomReporter._attach_identified_licenses
# ---------------------------------------------------------------------------


def test_attach_identified_licenses_adds_license_to_component():
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    SbomReporter._attach_identified_licenses(component, [lic])
    assert "MIT" in _get_license_ids(component)


def test_attach_identified_licenses_adds_confidence_property():
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    SbomReporter._attach_identified_licenses(component, [lic])
    prop_value = _get_property_value(component, "dfetch:license:MIT:confidence")
    assert prop_value == "0.95"


def test_attach_identified_licenses_confidence_formatted_two_decimal_places():
    component = _make_component()
    lic = _make_license(spdx_id="Apache-2.0", probability=0.9)
    SbomReporter._attach_identified_licenses(component, [lic])
    prop_value = _get_property_value(component, "dfetch:license:Apache-2.0:confidence")
    assert prop_value == "0.90"


def test_attach_identified_licenses_multiple_licenses():
    component = _make_component()
    lic1 = _make_license(spdx_id="MIT", probability=0.95)
    lic2 = _make_license(name="Apache 2.0", spdx_id="Apache-2.0", probability=0.88)
    SbomReporter._attach_identified_licenses(component, [lic1, lic2])
    ids = _get_license_ids(component)
    assert "MIT" in ids
    assert "Apache-2.0" in ids


def test_attach_identified_licenses_uses_name_as_label_when_no_spdx_id():
    """When spdx_id is empty, the name is used as the confidence property label."""
    component = _make_component()
    lic = DfetchLicense(
        name="Custom License", spdx_id="", trove_classifier=None, probability=0.85
    )
    SbomReporter._attach_identified_licenses(component, [lic])
    prop_value = _get_property_value(component, "dfetch:license:Custom License:confidence")
    assert prop_value == "0.85"


def test_attach_identified_licenses_embeds_text_in_license():
    """If the DfetchLicense has text, it should be embedded in the CycloneDX license."""
    component = _make_component()
    raw_text = "MIT License\nCopyright 2024"
    lic = _make_license(spdx_id="MIT", probability=0.95, text=raw_text)
    SbomReporter._attach_identified_licenses(component, [lic])
    cdx_lic = next(iter(component.licenses))
    assert cdx_lic.text is not None
    expected_b64 = base64.b64encode(raw_text.encode("utf-8")).decode("ascii")
    assert cdx_lic.text.content == expected_b64


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – not scanned
# ---------------------------------------------------------------------------


def test_apply_licenses_not_scanned_adds_nothing():
    """When was_scanned=False no properties or licenses are added."""
    component = _make_component()
    scan = LicenseScanResult(was_scanned=False)
    SbomReporter._apply_licenses(component, scan)
    assert len(list(component.licenses)) == 0
    assert len(list(component.properties)) == 0


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – scanned with identified licenses
# ---------------------------------------------------------------------------


def test_apply_licenses_identified_adds_tool_property():
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
    with patch("dfetch.reporting.sbom_reporter.INFER_LICENSE_VERSION", "1.2.3"):
        SbomReporter._apply_licenses(component, scan)
    assert _get_property_value(component, "dfetch:license:tool") == "infer-license 1.2.3"


def test_apply_licenses_identified_adds_threshold_property():
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    assert _get_property_value(component, "dfetch:license:threshold") == "0.80"


def test_apply_licenses_identified_adds_license_to_component():
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    assert "MIT" in _get_license_ids(component)


def test_apply_licenses_identified_no_noassertion():
    """When a license is identified NOASSERTION should not be present."""
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    assert "NOASSERTION" not in _get_license_ids(component)


def test_apply_licenses_identified_no_finding_property():
    """No dfetch:license:finding property when a license is identified."""
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    assert _get_property_value(component, "dfetch:license:finding") is None


def test_apply_licenses_identified_adds_confidence_property():
    """Confidence property is set for identified licenses."""
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    assert _get_property_value(component, "dfetch:license:MIT:confidence") == "0.95"


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – scanned with unclassified files
# ---------------------------------------------------------------------------


def test_apply_licenses_unclassified_sets_noassertion():
    component = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"], was_scanned=True, threshold=0.80
    )
    SbomReporter._apply_licenses(component, scan)
    assert "NOASSERTION" in _get_license_ids(component)


def test_apply_licenses_unclassified_sets_noassertion_reason():
    component = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"], was_scanned=True, threshold=0.80
    )
    SbomReporter._apply_licenses(component, scan)
    reason = _get_property_value(component, "dfetch:license:noassertion:reason")
    assert reason == "UNCLASSIFIABLE_LICENSE_TEXT"


def test_apply_licenses_unclassified_sets_finding_property():
    component = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"], was_scanned=True, threshold=0.80
    )
    SbomReporter._apply_licenses(component, scan)
    finding = _get_property_value(component, "dfetch:license:finding")
    assert "LICENSE" in finding
    assert "could not be classified" in finding


def test_apply_licenses_unclassified_multiple_files_sorted():
    """Multiple unclassified files appear sorted in the finding property."""
    component = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["COPYING", "LICENSE"], was_scanned=True, threshold=0.80
    )
    SbomReporter._apply_licenses(component, scan)
    finding = _get_property_value(component, "dfetch:license:finding")
    # sorted: COPYING before LICENSE
    assert "COPYING, LICENSE" in finding


def test_apply_licenses_unclassified_adds_tool_and_threshold():
    component = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"], was_scanned=True, threshold=0.80
    )
    with patch("dfetch.reporting.sbom_reporter.INFER_LICENSE_VERSION", "2.0"):
        SbomReporter._apply_licenses(component, scan)
    assert _get_property_value(component, "dfetch:license:tool") == "infer-license 2.0"
    assert _get_property_value(component, "dfetch:license:threshold") == "0.80"


def test_apply_licenses_unclassified_noassertion_has_acknowledgement():
    """NOASSERTION license entry has acknowledgement=CONCLUDED."""
    component = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"], was_scanned=True, threshold=0.80
    )
    SbomReporter._apply_licenses(component, scan)
    noassertion_lic = next(
        (lic for lic in component.licenses if lic.id == "NOASSERTION"), None
    )
    assert noassertion_lic is not None
    assert noassertion_lic.acknowledgement == LicenseAcknowledgement.CONCLUDED


def test_apply_licenses_unclassified_noassertion_has_text():
    """NOASSERTION license entry has a human-readable text explanation."""
    component = _make_component()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"], was_scanned=True, threshold=0.80
    )
    SbomReporter._apply_licenses(component, scan)
    noassertion_lic = next(
        (lic for lic in component.licenses if lic.id == "NOASSERTION"), None
    )
    assert noassertion_lic is not None
    assert noassertion_lic.text is not None
    assert "LICENSE" in noassertion_lic.text.content


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – scanned with no license file
# ---------------------------------------------------------------------------


def test_apply_licenses_no_license_file_sets_noassertion():
    component = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    assert "NOASSERTION" in _get_license_ids(component)


def test_apply_licenses_no_license_file_sets_reason():
    component = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    reason = _get_property_value(component, "dfetch:license:noassertion:reason")
    assert reason == "NO_LICENSE_FILE"


def test_apply_licenses_no_license_file_sets_finding_property():
    component = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    finding = _get_property_value(component, "dfetch:license:finding")
    assert finding == "No license file found in source tree"


def test_apply_licenses_no_license_file_noassertion_has_acknowledgement():
    component = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    noassertion_lic = next(
        (lic for lic in component.licenses if lic.id == "NOASSERTION"), None
    )
    assert noassertion_lic is not None
    assert noassertion_lic.acknowledgement == LicenseAcknowledgement.CONCLUDED


def test_apply_licenses_no_license_file_noassertion_text_explains_reason():
    component = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    noassertion_lic = next(
        (lic for lic in component.licenses if lic.id == "NOASSERTION"), None
    )
    assert noassertion_lic is not None
    assert noassertion_lic.text is not None
    assert "No license file found" in noassertion_lic.text.content


def test_apply_licenses_no_license_file_adds_tool_and_threshold():
    component = _make_component()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)
    with patch("dfetch.reporting.sbom_reporter.INFER_LICENSE_VERSION", "0.5.0"):
        SbomReporter._apply_licenses(component, scan)
    assert _get_property_value(component, "dfetch:license:tool") == "infer-license 0.5.0"
    assert _get_property_value(component, "dfetch:license:threshold") == "0.80"


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – threshold formatting
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "threshold, expected",
    [
        (0.80, "0.80"),
        (0.5, "0.50"),
        (1.0, "1.00"),
        (0.0, "0.00"),
    ],
)
def test_apply_licenses_threshold_formatted_two_decimal_places(threshold, expected):
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.95)
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=threshold)
    SbomReporter._apply_licenses(component, scan)
    assert _get_property_value(component, "dfetch:license:threshold") == expected


# ---------------------------------------------------------------------------
# SbomReporter._apply_licenses – boundary: threshold = probability (>=)
# ---------------------------------------------------------------------------


def test_apply_licenses_exactly_at_threshold_is_identified():
    """The >= comparison means a license at exactly the threshold is accepted."""
    component = _make_component()
    lic = _make_license(spdx_id="MIT", probability=0.80)
    # Simulate that Report._determine_licenses already accepted it (probability >= threshold)
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)
    SbomReporter._apply_licenses(component, scan)
    assert "MIT" in _get_license_ids(component)
    assert "NOASSERTION" not in _get_license_ids(component)