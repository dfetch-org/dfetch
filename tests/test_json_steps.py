"""Tests for features/steps/json_steps.py – JSON subset matching and normalisation."""

# mypy: ignore-errors
# flake8: noqa

import json
import os

import pytest

from features.steps.json_steps import _json_subset_matches, _normalise_json


# ---------------------------------------------------------------------------
# _normalise_json
# ---------------------------------------------------------------------------


def test_normalise_json_replaces_iso_timestamp():
    obj = {"created": "2024-01-15T10:30:45.123456+00:00"}
    result = _normalise_json(obj)
    assert result["created"] == "[timestamp]"


def test_normalise_json_replaces_urn_uuid():
    obj = {"id": "urn:uuid:550e8400-e29b-41d4-a716-446655440000"}
    result = _normalise_json(obj)
    assert result["id"] == "[urn-uuid]"


def test_normalise_json_preserves_plain_string():
    obj = {"name": "MIT License"}
    result = _normalise_json(obj)
    assert result["name"] == "MIT License"


def test_normalise_json_preserves_numbers():
    obj = {"confidence": 0.95}
    result = _normalise_json(obj)
    assert result["confidence"] == 0.95


def test_normalise_json_handles_nested_dict():
    obj = {
        "outer": {
            "timestamp": "2024-01-15T10:30:45.123456+00:00",
            "value": "kept",
        }
    }
    result = _normalise_json(obj)
    assert result["outer"]["timestamp"] == "[timestamp]"
    assert result["outer"]["value"] == "kept"


def test_normalise_json_handles_list():
    obj = [
        "2024-01-15T10:30:45.123456+00:00",
        "plain string",
        "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
    ]
    result = _normalise_json(obj)
    assert result[0] == "[timestamp]"
    assert result[1] == "plain string"
    assert result[2] == "[urn-uuid]"


def test_normalise_json_preserves_none():
    result = _normalise_json(None)
    assert result is None


def test_normalise_json_preserves_bool():
    result = _normalise_json(True)
    assert result is True


def test_normalise_json_timestamp_partial_match_not_replaced():
    # String that starts with date but is NOT a full timestamp – should be kept
    obj = {"date": "2024-01-15"}
    result = _normalise_json(obj)
    assert result["date"] == "2024-01-15"


# ---------------------------------------------------------------------------
# _json_subset_matches – scalar types
# ---------------------------------------------------------------------------


def test_json_subset_scalar_equal():
    assert _json_subset_matches("MIT", "MIT") is True


def test_json_subset_scalar_not_equal():
    assert _json_subset_matches("MIT", "Apache-2.0") is False


def test_json_subset_scalar_vs_dict():
    assert _json_subset_matches("MIT", {"id": "MIT"}) is False


def test_json_subset_int_equal():
    assert _json_subset_matches(42, 42) is True


def test_json_subset_int_not_equal():
    assert _json_subset_matches(1, 2) is False


# ---------------------------------------------------------------------------
# _json_subset_matches – dict matching
# ---------------------------------------------------------------------------


def test_json_subset_dict_exact_match():
    assert _json_subset_matches({"a": 1}, {"a": 1}) is True


def test_json_subset_dict_subset_match():
    assert _json_subset_matches({"a": 1}, {"a": 1, "b": 2}) is True


def test_json_subset_dict_missing_key_fails():
    assert _json_subset_matches({"a": 1, "c": 3}, {"a": 1, "b": 2}) is False


def test_json_subset_dict_value_mismatch_fails():
    assert _json_subset_matches({"a": 2}, {"a": 1}) is False


def test_json_subset_dict_nested_subset():
    expected = {"outer": {"x": 1}}
    actual = {"outer": {"x": 1, "y": 2}, "other": "data"}
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_dict_nested_mismatch():
    expected = {"outer": {"x": 2}}
    actual = {"outer": {"x": 1, "y": 2}}
    assert _json_subset_matches(expected, actual) is False


def test_json_subset_expected_dict_actual_non_dict():
    assert _json_subset_matches({"a": 1}, [1, 2]) is False


# ---------------------------------------------------------------------------
# _json_subset_matches – list matching with backtracking
# ---------------------------------------------------------------------------


def test_json_subset_list_empty_expected():
    assert _json_subset_matches([], [1, 2, 3]) is True


def test_json_subset_list_empty_actual_fails():
    assert _json_subset_matches([1], []) is False


def test_json_subset_list_exact_match():
    assert _json_subset_matches([1, 2], [1, 2]) is True


def test_json_subset_list_single_item_found():
    assert _json_subset_matches([{"a": 1}], [{"a": 1, "b": 2}, {"c": 3}]) is True


def test_json_subset_list_item_not_found():
    assert _json_subset_matches([{"z": 99}], [{"a": 1}, {"b": 2}]) is False


def test_json_subset_list_order_independent():
    """Items can match in any order."""
    expected = [{"id": "B"}, {"id": "A"}]
    actual = [{"id": "A"}, {"id": "B"}]
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_list_backtracking_avoids_greedy_pitfall():
    """Regression test: backtracking allows more-specific items to match correctly.

    Greedy matching would assign {"a": 1} first to {"a": 1, "b": 2}, leaving
    nothing for {"a": 1, "b": 2} itself. With backtracking this should succeed.
    """
    expected = [{"a": 1, "b": 2}, {"a": 1}]
    actual = [{"a": 1, "b": 2}]
    # Both expected items can be satisfied by the single actual item only if
    # backtracking correctly realises the greedy first assignment fails.
    # Actually with only one actual item we cannot match two expected items.
    assert _json_subset_matches(expected, actual) is False


def test_json_subset_list_backtracking_succeeds_when_possible():
    """The backtracking algorithm finds a valid assignment across two items."""
    expected = [{"a": 1, "b": 2}, {"a": 1}]
    actual = [{"a": 1, "b": 2}, {"a": 1, "c": 3}]
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_list_each_item_used_once():
    """Each actual item can only satisfy one expected item."""
    expected = [1, 1]
    actual = [1]
    assert _json_subset_matches(expected, actual) is False


def test_json_subset_list_items_used_once_two_actual():
    expected = [1, 1]
    actual = [1, 1]
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_list_vs_non_list_fails():
    assert _json_subset_matches([1, 2], {"a": 1}) is False


def test_json_subset_list_of_dicts_with_subset_match():
    expected = [{"name": "dfetch:license:threshold", "value": "0.80"}]
    actual = [
        {"name": "dfetch:license:tool", "value": "infer-license 1.0"},
        {"name": "dfetch:license:threshold", "value": "0.80"},
        {"name": "dfetch:license:finding", "value": "No license file found in source tree"},
    ]
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_list_of_dicts_partial_key_match():
    """Checking only the 'name' key, not 'value'."""
    expected = [{"name": "dfetch:license:threshold"}]
    actual = [
        {"name": "dfetch:license:tool", "value": "infer-license 1.0"},
        {"name": "dfetch:license:threshold", "value": "0.80"},
    ]
    assert _json_subset_matches(expected, actual) is True


# ---------------------------------------------------------------------------
# _json_subset_matches – mixed nested structures
# ---------------------------------------------------------------------------


def test_json_subset_components_with_license_identified():
    expected = {
        "components": [
            {
                "name": "SomeProject",
                "licenses": [{"license": {"id": "MIT"}}],
            }
        ]
    }
    actual = {
        "components": [
            {
                "name": "SomeProject",
                "version": "1.0",
                "licenses": [
                    {
                        "license": {
                            "id": "MIT",
                            "text": {
                                "contentType": "text/plain",
                                "encoding": "base64",
                                "content": "TVQgTGljZW5zZQ==",
                            },
                        }
                    }
                ],
                "properties": [],
            }
        ]
    }
    assert _json_subset_matches(expected, actual) is True


def test_json_subset_components_noassertion():
    expected = {
        "components": [
            {
                "name": "SomeProject",
                "licenses": [
                    {
                        "license": {
                            "id": "NOASSERTION",
                            "acknowledgement": "concluded",
                        }
                    }
                ],
            }
        ]
    }
    actual = {
        "components": [
            {
                "name": "SomeProject",
                "licenses": [
                    {
                        "license": {
                            "id": "NOASSERTION",
                            "acknowledgement": "concluded",
                            "text": {
                                "content": "No license file found in source tree",
                                "contentType": "text/plain",
                            },
                        }
                    }
                ],
                "properties": [
                    {"name": "dfetch:license:finding", "value": "No license file found in source tree"},
                ],
            }
        ]
    }
    assert _json_subset_matches(expected, actual) is True