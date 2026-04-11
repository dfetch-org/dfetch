"""Unit tests for dfetch.util.license – LicenseScanResult and License changes."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import MagicMock, patch

import pytest

from dfetch.util.license import License, LicenseScanResult, guess_license_in_file


# ---------------------------------------------------------------------------
# LicenseScanResult – dataclass defaults and states
# ---------------------------------------------------------------------------


def test_license_scan_result_defaults():
    """Default LicenseScanResult has safe/empty values."""
    result = LicenseScanResult()
    assert result.identified == []
    assert result.unclassified_files == []
    assert result.was_scanned is False
    assert result.threshold == 0.0


def test_license_scan_result_not_scanned():
    """was_scanned=False represents a project that was never fetched."""
    result = LicenseScanResult(was_scanned=False)
    assert not result.was_scanned
    assert result.identified == []
    assert result.unclassified_files == []


def test_license_scan_result_identified():
    """was_scanned=True with identified licenses is the happy path."""
    lic = License(name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.95)
    result = LicenseScanResult(
        identified=[lic],
        was_scanned=True,
        threshold=0.80,
    )
    assert result.was_scanned is True
    assert len(result.identified) == 1
    assert result.identified[0].spdx_id == "MIT"
    assert result.unclassified_files == []
    assert result.threshold == 0.80


def test_license_scan_result_unclassified():
    """was_scanned=True with unclassified_files and no identified is the unclassifiable case."""
    result = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )
    assert result.was_scanned is True
    assert result.identified == []
    assert result.unclassified_files == ["LICENSE"]


def test_license_scan_result_no_license_file():
    """was_scanned=True with empty identified and empty unclassified_files means no file found."""
    result = LicenseScanResult(was_scanned=True, threshold=0.80)
    assert result.was_scanned is True
    assert result.identified == []
    assert result.unclassified_files == []


def test_license_scan_result_multiple_identified():
    """Multiple identified licenses are all stored."""
    lic1 = License(name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.95)
    lic2 = License(name="Apache 2.0", spdx_id="Apache-2.0", trove_classifier=None, probability=0.90)
    result = LicenseScanResult(identified=[lic1, lic2], was_scanned=True)
    assert len(result.identified) == 2


def test_license_scan_result_multiple_unclassified():
    """Multiple unclassified files are all stored."""
    result = LicenseScanResult(
        unclassified_files=["LICENSE", "COPYING"],
        was_scanned=True,
    )
    assert len(result.unclassified_files) == 2


# ---------------------------------------------------------------------------
# License.from_inferred – text field propagation
# ---------------------------------------------------------------------------


def _make_inferred_license(name="MIT License", shortname="MIT", trove="License :: OSI Approved :: MIT License"):
    """Build a minimal infer-license InferredLicense-like mock."""
    mock = MagicMock()
    mock.name = name
    mock.shortname = shortname
    mock.trove_classifier = trove
    return mock


def test_license_from_inferred_without_text():
    """License.from_inferred without text leaves text as None."""
    inferred = _make_inferred_license()
    lic = License.from_inferred(inferred, probability=0.92)
    assert lic.text is None
    assert lic.name == "MIT License"
    assert lic.spdx_id == "MIT"
    assert lic.probability == 0.92
    assert lic.trove_classifier == "License :: OSI Approved :: MIT License"


def test_license_from_inferred_with_text():
    """License.from_inferred stores provided license text."""
    inferred = _make_inferred_license()
    raw_text = "MIT License\n\nCopyright (c) 2024 Test\n"
    lic = License.from_inferred(inferred, probability=0.95, text=raw_text)
    assert lic.text == raw_text


def test_license_from_inferred_with_none_text_explicitly():
    """Explicitly passing text=None behaves the same as omitting it."""
    inferred = _make_inferred_license()
    lic = License.from_inferred(inferred, probability=0.85, text=None)
    assert lic.text is None


def test_license_from_inferred_probability_stored():
    """Probability is stored verbatim on the License."""
    inferred = _make_inferred_license()
    lic = License.from_inferred(inferred, probability=0.80)
    assert lic.probability == 0.80


def test_license_text_field_default_on_direct_construction():
    """License constructed directly has text=None by default."""
    lic = License(name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.9)
    assert lic.text is None


def test_license_text_field_can_be_set_directly():
    """License.text can be set during direct construction."""
    lic = License(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.9, text="some text"
    )
    assert lic.text == "some text"


# ---------------------------------------------------------------------------
# guess_license_in_file – text is forwarded to returned License
# ---------------------------------------------------------------------------


def test_guess_license_in_file_returns_text(tmp_path):
    """guess_license_in_file passes the file text to License.from_inferred."""
    license_file = tmp_path / "LICENSE"
    license_text = "MIT License\nPermission is hereby granted..."
    license_file.write_text(license_text, encoding="utf-8")

    mock_inferred = _make_inferred_license()
    with patch("dfetch.util.license.infer_license.api.probabilities") as mock_prob:
        mock_prob.return_value = [(mock_inferred, 0.95)]
        result = guess_license_in_file(str(license_file))

    assert result is not None
    assert result.text == license_text


def test_guess_license_in_file_returns_none_when_no_probabilities(tmp_path):
    """guess_license_in_file returns None when infer_license returns empty list."""
    license_file = tmp_path / "LICENSE"
    license_file.write_text("some random text", encoding="utf-8")

    with patch("dfetch.util.license.infer_license.api.probabilities") as mock_prob:
        mock_prob.return_value = []
        result = guess_license_in_file(str(license_file))

    assert result is None