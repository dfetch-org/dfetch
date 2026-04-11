"""Unit tests for features/steps/json_steps.py – _json_subset_matches and _normalise_json."""

# mypy: ignore-errors
# flake8: noqa

import json
import os

import pytest

from features.steps.json_steps import _json_subset_matches, _normalise_json, check_json_subset


# ---------------------------------------------------------------------------
# _normalise_json
# ---------------------------------------------------------------------------


def test_normalise_json_replaces_iso_timestamp():
    result = _normalise_json("2024-01-15T12:34:56.789012+00:00")
    assert result == "[timestamp]"


def test_normalise_json_replaces_urn_uuid():
    result = _normalise_json("urn:uuid:550e8400-e29b-41d4-a716-446655440000")
    assert result == "[urn-uuid]"


def test_normalise_json_preserves_regular_string():
    result = _normalise_json("MIT")
    assert result == "MIT"


def test_normalise_json_preserves_empty_string():
    result = _normalise_json("")
    assert result == ""


def test_normalise_json_preserves_numeric():
    result = _normalise_json(42)
    assert result == 42


def test_normalise_json_preserves_boolean():
    assert _normalise_json(True) is True
    assert _normalise_json(False) is False


def test_normalise_json_preserves_none():
    assert _normalise_json(None) is None


def test_normalise_json_normalises_nested_dict():
    obj = {
        "name": "test",
        "timestamp": "2024-01-15T12:34:56.789012+00:00",
        "serial": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
    }
    result = _normalise_json(obj)
    assert result["name"] == "test"
    assert result["timestamp"] == "[timestamp]"
    assert result["serial"] == "[urn-uuid]"


def test_normalise_json_normalises_list_elements():
    items = [
        "2024-01-15T12:34:56.789012+00:00",
        "plain string",
        "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
    ]
    result = _normalise_json(items)
    assert result[0] == "[timestamp]"
    assert result[1] == "plain string"
    assert result[2] == "[urn-uuid]"


def test_normalise_json_nested_list_in_dict():
    obj = {
        "items": [
            {"ts": "2024-01-15T12:34:56.789012+00:00"},
            {"name": "keep"},
        ]
    }
    result = _normalise_json(obj)
    assert result["items"][0]["ts"] == "[timestamp]"
    assert result["items"][1]["name"] == "keep"


def test_normalise_json_string_not_matching_patterns_unchanged():
    # Close but not matching timestamp format
    result = _normalise_json("2024-01-15 12:34:56")
    assert result == "2024-01-15 12:34:56"


# ---------------------------------------------------------------------------
# _json_subset_matches – scalar matching
# ---------------------------------------------------------------------------


def test_json_subset_matches_equal_scalars():
    assert _json_subset_matches("MIT", "MIT") is True


def test_json_subset_matches_unequal_scalars():
    assert _json_subset_matches("MIT", "Apache-2.0") is False


def test_json_subset_matches_numeric():
    assert _json_subset_matches(42, 42) is True
    assert _json_subset_matches(42, 43) is False


# ---------------------------------------------------------------------------
# _json_subset_matches – dict matching
# ---------------------------------------------------------------------------


def test_json_subset_matches_exact_dict():
    assert _json_subset_matches({"a": 1}, {"a": 1}) is True


def test_json_subset_matches_dict_subset():
    """Expected is a strict subset of actual – should match."""
    assert _json_subset_matches({"a": 1}, {"a": 1, "b": 2}) is True


def test_json_subset_matches_dict_missing_key():
    """Expected has a key not present in actual – should not match."""
    assert _json_subset_matches({"a": 1, "c": 3}, {"a": 1, "b": 2}) is False


def test_json_subset_matches_dict_wrong_value():
    assert _json_subset_matches({"a": 1}, {"a": 2}) is False


def test_json_subset_matches_dict_vs_non_dict():
    assert _json_subset_matches({"a": 1}, [1, 2]) is False
    assert _json_subset_matches({"a": 1}, "string") is False


def test_json_subset_matches_nested_dict():
    expected = {"outer": {"inner": "value"}}
    actual = {"outer": {"inner": "value", "extra": "ignored"}}
    assert _json_subset_matches(expected, actual) is True


# ---------------------------------------------------------------------------
# _json_subset_matches – list matching (backtracking)
# ---------------------------------------------------------------------------


def test_json_subset_matches_list_empty_expected():
    """Empty expected list matches any actual list."""
    assert _json_subset_matches([], [1, 2, 3]) is True
    assert _json_subset_matches([], []) is True


def test_json_subset_matches_list_exact():
    assert _json_subset_matches([1, 2], [1, 2]) is True


def test_json_subset_matches_list_subset_present():
    assert _json_subset_matches([1], [1, 2, 3]) is True
    assert _json_subset_matches([2], [1, 2, 3]) is True
    assert _json_subset_matches([3], [1, 2, 3]) is True


def test_json_subset_matches_list_item_not_present():
    assert _json_subset_matches([4], [1, 2, 3]) is False


def test_json_subset_matches_list_vs_non_list():
    assert _json_subset_matches([1], "not a list") is False
    assert _json_subset_matches([1], {"a": 1}) is False


def test_json_subset_matches_list_backtracking_avoids_greedy_pitfall():
    """The backtracking algorithm should not claim the more-specific item greedily.

    Classic greedy failure:
        expected = [{"a": 1}, {"a": 1, "b": 2}]
        actual   = [{"a": 1, "b": 2}]

    Greedy matching would consume {"a": 1, "b": 2} for the first expected item
    (because it is a superset of {"a": 1}), leaving nothing for the second.
    With backtracking the algorithm discovers that assigning the single actual
    item to the second expected item satisfies both.
    """
    expected = [{"a": 1, "b": 2}, {"a": 1}]
    actual = [{"a": 1, "b": 2}]
    # The second expected is a subset of the only actual item; combined they
    # can't both be satisfied since there is only one actual item.
    # This should fail because we need two distinct actual items.
    assert _json_subset_matches(expected, actual) is False


def test_json_subset_matches_list_backtracking_succeeds_when_possible():
    """Both expected items can be matched when actual has enough entries."""
    expected = [{"a": 1, "b": 2}, {"a": 1}]
    actual = [{"a": 1, "b": 2}, {"a": 1, "c": 3}]
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_matches_list_order_independent():
    """Items in the expected list don't have to appear in the same order as actual."""
    expected = [{"name": "B"}, {"name": "A"}]
    actual = [{"name": "A", "val": 1}, {"name": "B", "val": 2}]
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_matches_list_of_dicts_subset():
    """Each expected dict is checked as a subset of a corresponding actual dict."""
    expected = [{"id": "MIT"}, {"id": "Apache-2.0"}]
    actual = [
        {"id": "MIT", "name": "MIT License"},
        {"id": "Apache-2.0", "name": "Apache License 2.0"},
        {"id": "GPL-2.0"},
    ]
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_matches_list_each_actual_used_once():
    """The same actual item cannot be used to satisfy two expected items."""
    expected = [{"id": "MIT"}, {"id": "MIT"}]
    actual = [{"id": "MIT"}]
    # Only one MIT in actual; can't satisfy two expected MITs
    assert _json_subset_matches(expected, actual) is False


def test_json_subset_matches_deeply_nested():
    expected = {
        "components": [
            {
                "name": "my-lib",
                "licenses": [{"license": {"id": "MIT"}}],
            }
        ]
    }
    actual = {
        "components": [
            {
                "name": "my-lib",
                "version": "1.0",
                "licenses": [
                    {"license": {"id": "MIT", "name": "MIT License"}},
                ],
            }
        ]
    }
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_matches_deeply_nested_mismatch():
    expected = {
        "components": [
            {
                "name": "my-lib",
                "licenses": [{"license": {"id": "GPL-2.0"}}],
            }
        ]
    }
    actual = {
        "components": [
            {
                "name": "my-lib",
                "licenses": [{"license": {"id": "MIT"}}],
            }
        ]
    }
    assert _json_subset_matches(expected, actual) is False


# ---------------------------------------------------------------------------
# check_json_subset – integration with file I/O and substitutions
# ---------------------------------------------------------------------------


def test_check_json_subset_passes_when_subset_matches(tmp_path):
    actual = {"name": "SomeProject", "version": "1.0", "extra": "ignored"}
    json_file = tmp_path / "report.json"
    json_file.write_text(json.dumps(actual), encoding="utf-8")

    context = object()  # no archive substitutions needed
    # Should not raise
    check_json_subset(str(json_file), '{"name": "SomeProject"}', context)


def test_check_json_subset_raises_when_not_subset(tmp_path):
    actual = {"name": "SomeProject"}
    json_file = tmp_path / "report.json"
    json_file.write_text(json.dumps(actual), encoding="utf-8")

    context = object()
    with pytest.raises(AssertionError, match="JSON subset mismatch"):
        check_json_subset(str(json_file), '{"name": "OtherProject"}', context)


def test_check_json_subset_normalises_timestamps(tmp_path):
    """Timestamps in actual are normalised so the expected placeholder matches."""
    actual = {
        "metadata": {"timestamp": "2024-06-01T10:00:00.000000+00:00"},
        "name": "test",
    }
    json_file = tmp_path / "report.json"
    json_file.write_text(json.dumps(actual), encoding="utf-8")

    context = object()
    # Use a different timestamp value; after normalisation both become [timestamp]
    check_json_subset(
        str(json_file),
        '{"metadata": {"timestamp": "2024-01-01T00:00:00.000000+00:00"}}',
        context,
    )


def test_check_json_subset_substitutes_archive_url(tmp_path):
    """<archive-url> placeholder is replaced from context.archive_url."""
    actual = {"url": "http://example.com/archive.tar.gz"}
    json_file = tmp_path / "report.json"
    json_file.write_text(json.dumps(actual), encoding="utf-8")

    class FakeContext:
        archive_url = "http://example.com/archive.tar.gz"

    check_json_subset(
        str(json_file), '{"url": "<archive-url>"}', FakeContext()
    )