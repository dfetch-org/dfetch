"""Tests for dfetch.util.license (LicenseScanResult and License changes from PR #1112)."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import MagicMock, patch

import pytest

from dfetch.util.license import License, LicenseScanResult, guess_license_in_file


# ---------------------------------------------------------------------------
# License dataclass – new ``text`` field
# ---------------------------------------------------------------------------


def test_license_text_field_defaults_to_none():
    lic = License(
        name="MIT License",
        spdx_id="MIT",
        trove_classifier="License :: OSI Approved :: MIT License",
        probability=0.99,
    )
    assert lic.text is None


def test_license_text_field_stores_content():
    text = "MIT License\n\nCopyright (c) 2024 Test"
    lic = License(
        name="MIT License",
        spdx_id="MIT",
        trove_classifier=None,
        probability=0.99,
        text=text,
    )
    assert lic.text == text


def test_license_from_inferred_without_text():
    mock_inferred = MagicMock()
    mock_inferred.name = "MIT License"
    mock_inferred.shortname = "MIT"
    mock_inferred.trove_classifier = "License :: OSI Approved :: MIT License"

    lic = License.from_inferred(mock_inferred, 0.95)

    assert lic.name == "MIT License"
    assert lic.spdx_id == "MIT"
    assert lic.probability == 0.95
    assert lic.text is None


def test_license_from_inferred_with_text():
    mock_inferred = MagicMock()
    mock_inferred.name = "MIT License"
    mock_inferred.shortname = "MIT"
    mock_inferred.trove_classifier = "License :: OSI Approved :: MIT License"
    raw_text = "MIT License\n\nPermission is hereby granted..."

    lic = License.from_inferred(mock_inferred, 0.95, text=raw_text)

    assert lic.text == raw_text


def test_license_from_inferred_preserves_trove_classifier():
    mock_inferred = MagicMock()
    mock_inferred.name = "Apache Software License"
    mock_inferred.shortname = "Apache-2.0"
    mock_inferred.trove_classifier = (
        "License :: OSI Approved :: Apache Software License"
    )

    lic = License.from_inferred(mock_inferred, 0.88, text="Apache License 2.0 ...")

    assert lic.trove_classifier == (
        "License :: OSI Approved :: Apache Software License"
    )


# ---------------------------------------------------------------------------
# LicenseScanResult dataclass
# ---------------------------------------------------------------------------


def test_license_scan_result_defaults():
    result = LicenseScanResult()
    assert result.identified == []
    assert result.unclassified_files == []
    assert result.was_scanned is False
    assert result.threshold == 0.0


def test_license_scan_result_not_fetched():
    result = LicenseScanResult(was_scanned=False)
    assert not result.was_scanned
    assert result.identified == []
    assert result.unclassified_files == []


def test_license_scan_result_with_identified_licenses():
    lic = License(name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99)
    result = LicenseScanResult(
        identified=[lic],
        was_scanned=True,
        threshold=0.80,
    )
    assert result.was_scanned is True
    assert len(result.identified) == 1
    assert result.identified[0].spdx_id == "MIT"
    assert result.threshold == 0.80


def test_license_scan_result_with_unclassified_files():
    result = LicenseScanResult(
        unclassified_files=["LICENSE", "COPYING"],
        was_scanned=True,
        threshold=0.80,
    )
    assert result.was_scanned is True
    assert result.identified == []
    assert sorted(result.unclassified_files) == ["COPYING", "LICENSE"]


def test_license_scan_result_scanned_no_license_files():
    """was_scanned=True with no identified and no unclassified_files = no license found."""
    result = LicenseScanResult(was_scanned=True, threshold=0.80)
    assert result.was_scanned is True
    assert result.identified == []
    assert result.unclassified_files == []


def test_license_scan_result_threshold_stored():
    result = LicenseScanResult(was_scanned=True, threshold=0.75)
    assert result.threshold == 0.75


def test_license_scan_result_independent_lists():
    """Verify default_factory creates independent lists per instance."""
    r1 = LicenseScanResult()
    r2 = LicenseScanResult()
    r1.identified.append(
        License(name="MIT", spdx_id="MIT", trove_classifier=None, probability=0.99)
    )
    assert r2.identified == []


# ---------------------------------------------------------------------------
# guess_license_in_file – text is passed through to License
# ---------------------------------------------------------------------------


def test_guess_license_in_file_returns_none_for_missing_file(tmp_path):
    result = guess_license_in_file(tmp_path / "does_not_exist.txt")
    assert result is None


def test_guess_license_in_file_returns_none_when_no_probable_license(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.write_text("This is not a recognizable license text at all.")

    with patch("dfetch.util.license.infer_license.api.probabilities", return_value=[]):
        result = guess_license_in_file(str(license_file))

    assert result is None


def test_guess_license_in_file_embeds_license_text(tmp_path):
    """guess_license_in_file should store the file text in License.text."""
    license_file = tmp_path / "LICENSE"
    raw_text = "MIT License\n\nCopyright (c) 2024 Example"
    license_file.write_text(raw_text, encoding="utf-8")

    mock_inferred = MagicMock()
    mock_inferred.name = "MIT License"
    mock_inferred.shortname = "MIT"
    mock_inferred.trove_classifier = None

    with patch(
        "dfetch.util.license.infer_license.api.probabilities",
        return_value=[(mock_inferred, 0.97)],
    ):
        result = guess_license_in_file(str(license_file))

    assert result is not None
    assert result.text == raw_text
    assert result.probability == 0.97


def test_guess_license_in_file_handles_latin1_fallback(tmp_path):
    """Files with non-UTF-8 bytes should be decoded with latin-1 fallback."""
    license_file = tmp_path / "LICENSE"
    # Write bytes that are valid Latin-1 but invalid UTF-8
    license_file.write_bytes(b"MIT License\xf6\xe4\xfc")

    mock_inferred = MagicMock()
    mock_inferred.name = "MIT License"
    mock_inferred.shortname = "MIT"
    mock_inferred.trove_classifier = None

    with patch(
        "dfetch.util.license.infer_license.api.probabilities",
        return_value=[(mock_inferred, 0.92)],
    ):
        result = guess_license_in_file(str(license_file))

    assert result is not None
    assert result.text is not None
    # Latin-1 decoded string should contain the special chars
    assert "\xf6" in result.text