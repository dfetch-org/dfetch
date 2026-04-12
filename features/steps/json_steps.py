"""Steps and helpers for JSON-based feature tests."""

# pylint: disable=function-redefined, missing-function-docstring, import-error, not-callable
# pyright: reportRedeclaration=false, reportAttributeAccessIssue=false, reportCallIssue=false

import json
import os
import re
from typing import Union

from behave import then  # pylint: disable=no-name-in-module

from features.steps.generic_steps import apply_archive_substitutions

_iso_timestamp_value = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}$"
)
_urn_uuid_value = re.compile(
    r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _normalise_json(obj):
    """Replace dynamic scalar values (timestamps, UUIDs) with stable placeholders."""
    if isinstance(obj, str):
        if _iso_timestamp_value.match(obj):
            return "[timestamp]"
        if _urn_uuid_value.match(obj):
            return "[urn-uuid]"
        return obj
    if isinstance(obj, dict):
        return {k: _normalise_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalise_json(item) for item in obj]
    return obj


def _json_subset_matches(expected, actual) -> bool:
    """Return *True* when *expected* is a subset of *actual* (recursive).

    List matching uses backtracking so that all possible assignments between
    expected and actual items are explored.  This avoids the greedy pitfall
    where an earlier expected item claims the only actual item that a later,
    more specific expected item would need.
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(
            k in actual and _json_subset_matches(v, actual[k])
            for k, v in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False

        def _try_match(exp_index: int, used: set) -> bool:
            if exp_index == len(expected):
                return True
            exp_item = expected[exp_index]
            for i, act_item in enumerate(actual):
                if i not in used and _json_subset_matches(exp_item, act_item):
                    if _try_match(exp_index + 1, used | {i}):
                        return True
            return False

        return _try_match(0, set())
    return expected == actual


def check_json_subset(path: Union[str, os.PathLike], content: str, context) -> None:
    """Assert that a JSON file *contains* the given key-values (subset match).

    Dynamic placeholders (``<archive-sha256>``, ``<archive-url>``) in
    *content* are substituted with values from *context* before parsing.
    Dynamic values (timestamps, UUIDs) are normalised in both sides before
    comparison so that feature files can contain any placeholder value.
    """
    content = apply_archive_substitutions(content, context)

    with open(path, "r", encoding="UTF-8") as file_to_check:
        actual_json = json.load(file_to_check)

    expected_json = _normalise_json(json.loads(content))
    actual_json = _normalise_json(actual_json)

    assert _json_subset_matches(expected_json, actual_json), (
        f"JSON subset mismatch.\n"
        f"Expected subset:\n{json.dumps(expected_json, indent=4, sort_keys=True)}\n"
        f"Actual:\n{json.dumps(actual_json, indent=4, sort_keys=True)}"
    )


@then("the '{name}' json file includes")
def step_impl(context, name):
    """Partial JSON match - the expected JSON must be a *subset* of the actual file."""
    check_json_subset(name, context.text, context)
