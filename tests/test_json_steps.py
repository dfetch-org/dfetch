"""Tests for features/steps/json_steps.py — covering new helpers added in PR #1112.

Changed/added in this PR:
- ``_normalise_json(obj)`` — replaces timestamps and urn-uuids with stable placeholders.
- ``_json_subset_matches(expected, actual)`` — backtracking recursive subset match.
- ``check_json_subset(path, content, context)`` — file-based subset assertion with
  dynamic placeholder substitution.
"""

# mypy: ignore-errors
# flake8: noqa

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from features.steps.json_steps import (
    _json_subset_matches,
    _normalise_json,
    check_json_subset,
)


# ---------------------------------------------------------------------------
# _normalise_json
# ---------------------------------------------------------------------------


class TestNormaliseJson:
    """_normalise_json replaces dynamic values with stable placeholders."""

    def test_iso_timestamp_is_replaced(self):
        ts = "2024-01-15T12:34:56.789012+00:00"
        assert _normalise_json(ts) == "[timestamp]"

    def test_non_timestamp_string_unchanged(self):
        s = "MIT License"
        assert _normalise_json(s) == "MIT License"

    def test_urn_uuid_is_replaced(self):
        uuid = "urn:uuid:550e8400-e29b-41d4-a716-446655440000"
        assert _normalise_json(uuid) == "[urn-uuid]"

    def test_non_uuid_string_unchanged(self):
        s = "pkg:github/org/repo@v1.0"
        assert _normalise_json(s) == s

    def test_integer_unchanged(self):
        assert _normalise_json(42) == 42

    def test_none_unchanged(self):
        assert _normalise_json(None) is None

    def test_boolean_unchanged(self):
        assert _normalise_json(True) is True

    def test_dict_values_are_normalised(self):
        data = {"ts": "2024-01-15T12:34:56.789012+00:00", "name": "test"}
        result = _normalise_json(data)
        assert result == {"ts": "[timestamp]", "name": "test"}

    def test_nested_dict_normalised(self):
        data = {"outer": {"inner": "2024-01-15T12:34:56.123456+00:00"}}
        result = _normalise_json(data)
        assert result["outer"]["inner"] == "[timestamp]"

    def test_list_items_normalised(self):
        data = ["2024-01-15T12:34:56.789012+00:00", "static"]
        result = _normalise_json(data)
        assert result == ["[timestamp]", "static"]

    def test_mixed_nested_structure(self):
        data = {
            "metadata": {
                "timestamp": "2024-01-15T12:34:56.789012+00:00",
                "serialNumber": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
            },
            "components": [{"name": "my-lib", "version": "1.0.0"}],
        }
        result = _normalise_json(data)
        assert result["metadata"]["timestamp"] == "[timestamp]"
        assert result["metadata"]["serialNumber"] == "[urn-uuid]"
        assert result["components"][0]["name"] == "my-lib"

    @pytest.mark.parametrize(
        "ts",
        [
            "2024-01-15T12:34:56.000000+00:00",
            "2025-12-31T23:59:59.999999+05:30",
            "2000-06-01T00:00:00.123456+00:00",
        ],
    )
    def test_various_iso_timestamps_replaced(self, ts):
        assert _normalise_json(ts) == "[timestamp]"

    @pytest.mark.parametrize(
        "uuid",
        [
            "urn:uuid:00000000-0000-0000-0000-000000000000",
            "urn:uuid:ffffffff-ffff-ffff-ffff-ffffffffffff",
            "urn:uuid:12345678-1234-1234-1234-123456789abc",
        ],
    )
    def test_various_urn_uuids_replaced(self, uuid):
        assert _normalise_json(uuid) == "[urn-uuid]"


# ---------------------------------------------------------------------------
# _json_subset_matches — scalar comparisons
# ---------------------------------------------------------------------------


class TestJsonSubsetMatchesScalars:
    def test_equal_strings_match(self):
        assert _json_subset_matches("hello", "hello") is True

    def test_unequal_strings_do_not_match(self):
        assert _json_subset_matches("hello", "world") is False

    def test_equal_integers_match(self):
        assert _json_subset_matches(42, 42) is True

    def test_unequal_integers_do_not_match(self):
        assert _json_subset_matches(1, 2) is False

    def test_none_matches_none(self):
        assert _json_subset_matches(None, None) is True

    def test_none_does_not_match_string(self):
        assert _json_subset_matches(None, "text") is False


# ---------------------------------------------------------------------------
# _json_subset_matches — dict comparisons
# ---------------------------------------------------------------------------


class TestJsonSubsetMatchesDicts:
    def test_empty_expected_matches_any_dict(self):
        assert _json_subset_matches({}, {"a": 1, "b": 2}) is True

    def test_exact_dict_matches(self):
        assert _json_subset_matches({"a": 1}, {"a": 1}) is True

    def test_subset_dict_matches(self):
        assert _json_subset_matches({"a": 1}, {"a": 1, "b": 2}) is True

    def test_missing_key_fails(self):
        assert _json_subset_matches({"c": 3}, {"a": 1, "b": 2}) is False

    def test_wrong_value_fails(self):
        assert _json_subset_matches({"a": 99}, {"a": 1}) is False

    def test_expected_dict_vs_non_dict_fails(self):
        assert _json_subset_matches({"a": 1}, [1, 2, 3]) is False

    def test_nested_dict_subset(self):
        expected = {"outer": {"inner": "value"}}
        actual = {"outer": {"inner": "value", "extra": "ignored"}}
        assert _json_subset_matches(expected, actual) is True

    def test_nested_dict_mismatch(self):
        expected = {"outer": {"inner": "value"}}
        actual = {"outer": {"inner": "different"}}
        assert _json_subset_matches(expected, actual) is False


# ---------------------------------------------------------------------------
# _json_subset_matches — list comparisons
# ---------------------------------------------------------------------------


class TestJsonSubsetMatchesLists:
    def test_empty_expected_list_matches_any_list(self):
        assert _json_subset_matches([], [1, 2, 3]) is True

    def test_single_item_found_in_list(self):
        assert _json_subset_matches([{"a": 1}], [{"a": 1, "b": 2}]) is True

    def test_single_item_not_found_in_list(self):
        assert _json_subset_matches([{"a": 99}], [{"a": 1}]) is False

    def test_order_independent_matching(self):
        expected = [{"id": "B"}, {"id": "A"}]
        actual = [{"id": "A"}, {"id": "B"}]
        assert _json_subset_matches(expected, actual) is True

    def test_all_items_must_be_found(self):
        expected = [{"id": "A"}, {"id": "C"}]
        actual = [{"id": "A"}, {"id": "B"}]
        assert _json_subset_matches(expected, actual) is False

    def test_expected_list_vs_non_list_fails(self):
        assert _json_subset_matches([1, 2], {"a": 1}) is False

    def test_backtracking_avoids_greedy_pitfall(self):
        """The OLD greedy algorithm would have matched {"a": 1} against
        {"a": 1, "b": 2} first, leaving nothing for the more specific item.
        The new backtracking implementation should handle this correctly."""
        expected = [{"a": 1}, {"a": 1, "b": 2}]
        actual = [{"a": 1, "b": 2}]
        # actual has only one element; expected needs two distinct matches.
        # The only way to satisfy this is impossible → False.
        assert _json_subset_matches(expected, actual) is False

    def test_backtracking_succeeds_when_both_satisfied(self):
        expected = [{"a": 1}, {"a": 1, "b": 2}]
        actual = [{"a": 1}, {"a": 1, "b": 2}]
        assert _json_subset_matches(expected, actual) is True

    def test_backtracking_does_not_reuse_same_item(self):
        """Two expected items must match two distinct actual items."""
        expected = [{"x": 1}, {"x": 1}]
        actual = [{"x": 1}]  # Only one actual item
        assert _json_subset_matches(expected, actual) is False

    def test_list_subset_in_dict(self):
        expected = {"components": [{"name": "lib-a"}]}
        actual = {"components": [{"name": "lib-a", "version": "1.0"}, {"name": "lib-b"}]}
        assert _json_subset_matches(expected, actual) is True

    def test_list_of_lists(self):
        expected = [[1, 2]]
        actual = [[1, 2, 3], [4, 5]]
        assert _json_subset_matches(expected, actual) is True


# ---------------------------------------------------------------------------
# _json_subset_matches — regression: specific field only (name key check)
# ---------------------------------------------------------------------------


class TestJsonSubsetMatchesPropertyList:
    """Verify property-list matching as used in SBOM feature tests."""

    def test_property_subset_matches(self):
        expected = [
            {"name": "dfetch:license:finding", "value": "No license file found in source tree"},
        ]
        actual = [
            {"name": "dfetch:license:tool", "value": "infer-license 1.0"},
            {"name": "dfetch:license:threshold", "value": "0.80"},
            {"name": "dfetch:license:finding", "value": "No license file found in source tree"},
            {"name": "dfetch:license:noassertion:reason", "value": "NO_LICENSE_FILE"},
        ]
        assert _json_subset_matches(expected, actual) is True

    def test_property_subset_mismatch(self):
        expected = [{"name": "dfetch:license:finding", "value": "WRONG VALUE"}]
        actual = [
            {"name": "dfetch:license:finding", "value": "No license file found in source tree"},
        ]
        assert _json_subset_matches(expected, actual) is False

    def test_name_only_property_match(self):
        """A property check with only a 'name' key should match any actual entry with that name."""
        expected = [{"name": "dfetch:license:BSD-3-Clause:confidence"}]
        actual = [
            {"name": "dfetch:license:BSD-3-Clause:confidence", "value": "0.95"},
            {"name": "dfetch:license:threshold", "value": "0.80"},
        ]
        assert _json_subset_matches(expected, actual) is True


# ---------------------------------------------------------------------------
# check_json_subset — file-based integration
# ---------------------------------------------------------------------------


class TestCheckJsonSubset:
    def _make_context(self, **attrs):
        """Return a simple namespace object with only the given attributes.

        Using MagicMock would cause ``hasattr`` to return True for *every*
        attribute (auto-creating MagicMock values), which breaks
        ``apply_archive_substitutions`` when it tries to call ``str.replace``
        with a non-string value.
        """

        class _Ctx:
            pass

        ctx = _Ctx()
        for k, v in attrs.items():
            setattr(ctx, k, v)
        return ctx

    def _write_json(self, tmp_path, data: dict) -> str:
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_exact_match_passes(self, tmp_path):
        data = {"components": [{"name": "lib-a", "version": "1.0"}]}
        path = self._write_json(tmp_path, data)
        ctx = self._make_context()
        content = json.dumps({"components": [{"name": "lib-a"}]})
        check_json_subset(path, content, ctx)  # Should not raise

    def test_subset_mismatch_raises(self, tmp_path):
        data = {"components": [{"name": "lib-a"}]}
        path = self._write_json(tmp_path, data)
        ctx = self._make_context()
        content = json.dumps({"components": [{"name": "lib-b"}]})
        with pytest.raises(AssertionError, match="JSON subset mismatch"):
            check_json_subset(path, content, ctx)

    def test_dynamic_timestamps_normalised_both_sides(self, tmp_path):
        actual_ts = "2024-01-15T12:34:56.789012+00:00"
        expected_ts = "2099-12-31T00:00:00.000000+00:00"  # Different timestamp
        data = {"metadata": {"timestamp": actual_ts}}
        path = self._write_json(tmp_path, data)
        ctx = self._make_context()
        content = json.dumps({"metadata": {"timestamp": expected_ts}})
        # Both are normalised to [timestamp] so they match
        check_json_subset(path, content, ctx)

    def test_dynamic_uuid_normalised(self, tmp_path):
        actual_uuid = "urn:uuid:550e8400-e29b-41d4-a716-446655440000"
        expected_uuid = "urn:uuid:12345678-1234-1234-1234-123456789abc"
        data = {"serialNumber": actual_uuid}
        path = self._write_json(tmp_path, data)
        ctx = self._make_context()
        content = json.dumps({"serialNumber": expected_uuid})
        check_json_subset(path, content, ctx)  # Should not raise

    def test_archive_url_placeholder_substituted(self, tmp_path):
        real_url = "http://example.com/my.tar.gz"
        data = {"url": real_url}
        path = self._write_json(tmp_path, data)
        ctx = self._make_context(archive_url=real_url)
        content = json.dumps({"url": "<archive-url>"})
        check_json_subset(path, content, ctx)  # Should not raise

    def test_license_base64_placeholder_substituted(self, tmp_path):
        import base64 as b64

        raw = "MIT License text"
        encoded = b64.b64encode(raw.encode()).decode("ascii")
        data = {"licenses": [{"license": {"text": {"content": encoded}}}]}
        path = self._write_json(tmp_path, data)
        ctx = self._make_context(license_base64=encoded)
        content = json.dumps({"licenses": [{"license": {"text": {"content": "<license-base64>"}}}]})
        check_json_subset(path, content, ctx)  # Should not raise

    def test_error_message_shows_expected_and_actual(self, tmp_path):
        data = {"name": "actual"}
        path = self._write_json(tmp_path, data)
        ctx = self._make_context()
        content = json.dumps({"name": "expected"})
        with pytest.raises(AssertionError) as exc_info:
            check_json_subset(path, content, ctx)
        msg = str(exc_info.value)
        assert "Expected subset" in msg
        assert "Actual" in msg