"""Tests for dfetch.util.license — covering changes introduced in PR #1112/#1116.

Changes under test:
- ``License.text`` field (new).
- ``License.from_inferred()`` now accepts an optional *text* parameter.
- ``LicenseScanResult`` dataclass (new): three distinct states.
- ``guess_license_in_file()`` now passes ``text=`` to ``License.from_inferred``.
"""

# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import MagicMock, patch

import pytest

from dfetch.util.license import (
    License,
    LicenseScanResult,
    guess_license_in_file,
    is_license_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inferred(name="MIT License", shortname="MIT", trove=None):
    """Return a minimal mock of infer_license.types.License."""
    m = MagicMock()
    m.name = name
    m.shortname = shortname
    m.trove_classifier = trove
    return m


# ---------------------------------------------------------------------------
# License.text field
# ---------------------------------------------------------------------------


class TestLicenseTextField:
    """License.text is optional and defaults to None."""

    def test_text_defaults_to_none(self):
        lic = License(
            name="MIT License",
            spdx_id="MIT",
            trove_classifier=None,
            probability=0.95,
        )
        assert lic.text is None

    def test_text_can_be_set(self):
        lic = License(
            name="MIT License",
            spdx_id="MIT",
            trove_classifier=None,
            probability=0.95,
            text="raw license text",
        )
        assert lic.text == "raw license text"


# ---------------------------------------------------------------------------
# License.from_inferred() with text parameter
# ---------------------------------------------------------------------------


class TestLicenseFromInferred:
    """License.from_inferred() stores the optional *text* argument."""

    def test_from_inferred_without_text(self):
        inferred = _make_inferred()
        lic = License.from_inferred(inferred, probability=0.90)
        assert lic.name == "MIT License"
        assert lic.spdx_id == "MIT"
        assert lic.probability == 0.90
        assert lic.text is None

    def test_from_inferred_with_text(self):
        inferred = _make_inferred()
        lic = License.from_inferred(inferred, probability=0.85, text="license body")
        assert lic.text == "license body"

    def test_from_inferred_propagates_trove_classifier(self):
        inferred = _make_inferred(trove="License :: OSI Approved :: MIT License")
        lic = License.from_inferred(inferred, probability=1.0)
        assert lic.trove_classifier == "License :: OSI Approved :: MIT License"

    def test_from_inferred_text_none_explicit(self):
        inferred = _make_inferred()
        lic = License.from_inferred(inferred, probability=0.99, text=None)
        assert lic.text is None


# ---------------------------------------------------------------------------
# LicenseScanResult — construction & field defaults
# ---------------------------------------------------------------------------


class TestLicenseScanResultDefaults:
    """LicenseScanResult has sensible defaults for all three states."""

    def test_default_state_is_not_scanned(self):
        result = LicenseScanResult()
        assert result.was_scanned is False
        assert result.identified == []
        assert result.unclassified_files == []
        assert result.threshold == 0.0

    def test_not_fetched_state(self):
        result = LicenseScanResult(was_scanned=False)
        assert result.was_scanned is False
        assert result.identified == []
        assert result.unclassified_files == []


class TestLicenseScanResultIdentified:
    """State: scanned and license was identified."""

    def test_identified_licenses(self):
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

    def test_multiple_identified_licenses(self):
        lic1 = License(name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.95)
        lic2 = License(name="Apache License 2.0", spdx_id="Apache-2.0", trove_classifier=None, probability=0.91)
        result = LicenseScanResult(
            identified=[lic1, lic2],
            was_scanned=True,
            threshold=0.80,
        )
        assert len(result.identified) == 2


class TestLicenseScanResultUnclassified:
    """State: scanned, license file present but unclassifiable."""

    def test_unclassified_files(self):
        result = LicenseScanResult(
            unclassified_files=["LICENSE"],
            was_scanned=True,
            threshold=0.80,
        )
        assert result.was_scanned is True
        assert result.identified == []
        assert result.unclassified_files == ["LICENSE"]

    def test_multiple_unclassified_files(self):
        result = LicenseScanResult(
            unclassified_files=["LICENSE", "COPYING"],
            was_scanned=True,
            threshold=0.80,
        )
        assert len(result.unclassified_files) == 2


class TestLicenseScanResultNoLicenseFile:
    """State: scanned, no license file found at all."""

    def test_no_license_file(self):
        result = LicenseScanResult(was_scanned=True, threshold=0.80)
        assert result.was_scanned is True
        assert result.identified == []
        assert result.unclassified_files == []


# ---------------------------------------------------------------------------
# LicenseScanResult — mutable default fields are independent per instance
# ---------------------------------------------------------------------------


def test_license_scan_result_mutable_fields_are_independent():
    """Each LicenseScanResult instance must have its own list objects."""
    r1 = LicenseScanResult(was_scanned=True)
    r2 = LicenseScanResult(was_scanned=True)
    r1.identified.append(
        License(name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.9)
    )
    assert r2.identified == [], "Mutable default leaked between instances"


# ---------------------------------------------------------------------------
# LicenseScanResult — threshold is preserved
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "threshold",
    [0.0, 0.50, 0.80, 1.0],
)
def test_license_scan_result_threshold_stored(threshold):
    result = LicenseScanResult(was_scanned=True, threshold=threshold)
    assert result.threshold == threshold


# ---------------------------------------------------------------------------
# guess_license_in_file() — text is embedded in returned License
# ---------------------------------------------------------------------------


class TestGuessLicenseInFileTextEmbedding:
    """guess_license_in_file must pass the raw text to License.from_inferred."""

    def test_returns_none_when_file_not_found(self, tmp_path):
        result = guess_license_in_file(tmp_path / "nonexistent_LICENSE")
        assert result is None

    def test_returns_none_for_unrecognised_text(self, tmp_path):
        license_file = tmp_path / "LICENSE"
        license_file.write_text("This is not a real license file at all. Gibberish.")
        with patch("infer_license.api.probabilities", return_value=[]):
            result = guess_license_in_file(license_file)
        assert result is None

    def test_text_is_embedded_in_result(self, tmp_path):
        """The raw license text read from disk must be stored on the License object."""
        license_content = "MIT License\nCopyright (c) 2024 Test"
        license_file = tmp_path / "LICENSE"
        license_file.write_text(license_content, encoding="utf-8")

        inferred_mock = _make_inferred()
        with patch("infer_license.api.probabilities", return_value=[(inferred_mock, 0.95)]):
            result = guess_license_in_file(license_file)

        assert result is not None
        assert result.text == license_content

    def test_latin1_fallback_text_is_embedded(self, tmp_path):
        """Latin-1 encoded license files should have their text embedded too."""
        license_content = "Licença MIT\nCopyright © 2024"
        license_file = tmp_path / "LICENSE"
        license_file.write_bytes(license_content.encode("latin-1"))

        inferred_mock = _make_inferred()
        with patch("infer_license.api.probabilities", return_value=[(inferred_mock, 0.92)]):
            result = guess_license_in_file(license_file)

        assert result is not None
        # Text should be the latin-1 decoded string
        assert "Licença MIT" in result.text

    def test_returns_none_on_permission_error(self, tmp_path):
        license_file = tmp_path / "LICENSE"
        license_file.write_text("something")
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = guess_license_in_file(license_file)
        assert result is None

    def test_returns_none_on_is_a_directory_error(self, tmp_path):
        with patch("builtins.open", side_effect=IsADirectoryError("is dir")):
            result = guess_license_in_file(tmp_path / "LICENSE")
        assert result is None


# ---------------------------------------------------------------------------
# is_license_file — unchanged but sanity-checked as part of this module
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("LICENSE", True),
        ("license", True),
        ("LICENSE.md", True),
        ("LICENSE.txt", True),
        ("LICENCE", True),
        ("licence", True),
        ("COPYING", True),
        ("copying.txt", True),
        ("COPYRIGHT", True),
        ("copyright.txt", True),
        ("README.md", False),
        ("setup.py", False),
        ("main.c", False),
        ("unlicensed.txt", False),  # Does not match the glob patterns
    ],
)
def test_is_license_file(filename, expected):
    assert is_license_file(filename) is expected