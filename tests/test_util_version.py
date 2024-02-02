"""Test the check command."""

# mypy: ignore-errors
# flake8: noqa

import pytest
from semver.version import Version

import dfetch.util.versions


@pytest.mark.parametrize(
    "name, tag_string, expected_version, expected_prefix, expected_rest",
    [
        (
            "prefix",
            "module/1.2.3",
            Version(major=1, minor=2, patch=3),
            "module/",
            "",
        ),
        (
            "prefix-lower-v",
            "module/v1.2.3",
            Version(major=1, minor=2, patch=3),
            "module/",
            "",
        ),
        (
            "prefix-upper-v",
            "module/V1.2.3",
            Version(major=1, minor=2, patch=3),
            "module/",
            "",
        ),
        (
            "prefix-multi-v",
            "vvV1.2.3",
            Version(major=1, minor=2, patch=3),
            "vv",
            "",
        ),
        (
            "prefix-multi-versions",
            "v1.2.3-v2.3.4",
            Version(major=1, minor=2, patch=3),
            "",
            "-v2.3.4",
        ),
        ("empty", "", Version(major=0, minor=0, patch=0), "", ""),
        ("only-major-minor", "1.2", Version(major=1, minor=2, patch=0), "", ""),
        (
            "only-major-minor-lower-v",
            "v1.2",
            Version(major=1, minor=2, patch=0),
            "",
            "",
        ),
        (
            "only-major-minor-upper-v",
            "V1.2",
            Version(major=1, minor=2, patch=0),
            "",
            "",
        ),
        ("only-major-lower-v", "v1", Version(major=1, minor=0, patch=0), "", ""),
        ("only-major-upper-v", "V1", Version(major=1, minor=0, patch=0), "", ""),
        ("only-major", "1", Version(major=1, minor=0, patch=0), "", ""),
        ("only-major", "1", Version(major=1, minor=0, patch=0), "", ""),
    ],
)
def test_version_parsing(
    name, tag_string, expected_version, expected_prefix, expected_rest
):
    prefix, version, rest = dfetch.util.versions.coerce(tag_string)

    assert expected_prefix == prefix
    assert expected_rest == rest

    if tag_string:
        assert expected_version == version


@pytest.mark.parametrize(
    "name, current_tag, available_tags, expected_tag",
    [
        ("single-available-tags", "v1.0.0", ["v1.0.0"], "v1.0.0"),
        (
            "multiple-available-tags-diff-versions",
            "v2.0.0",
            ["v1.0.0", "v2.0.0", "v3.0.0"],
            "v3.0.0",
        ),
        (
            "multiple-available-tags-same-versions",
            "v1.0.0",
            ["v1.0.0", "v1.0.0-alpha", "v1.0.0-beta"],
            "v1.0.0",
        ),
        (
            "multiple-available-tags-diff-prefix",
            "bla/v1.0.0",
            ["bla/v1.0.0", "ignore/v1.0.1", "bla/v0.9.0"],
            "bla/v1.0.0",
        ),
        (
            "no-available-tags",
            "v1.0.0",
            [],
            "v1.0.0",
        ),
        (
            "without-version",
            "no-version",
            ["no-version", "v1.0.0", "v2.0.0"],
            "no-version",
        ),
        (
            "newer available",
            "1.2.3",
            ["1.2.3", "1.2.4"],
            "1.2.4",
        ),
        (
            "same available",
            "1.2.0",
            ["1.2.0"],
            "1.2.0",
        ),
        (
            "no newer available",
            "1.2.4",
            ["1.2.1", "1.2.2", "1.2.4"],
            "1.2.4",
        ),
        (
            "non-existent tag",
            "5.2.3",
            ["1.2.1", "1.2.2", "1.2.4"],
            "5.2.3",
        ),
        (
            "non-numerical tag",
            "some-word",
            ["some-word", "some-other"],
            "some-word",
        ),
        ("issue", "non-existent-tag", ["v3.3", "v3.4"], "non-existent-tag"),
    ],
)
def test_latest_tag_from_list(name, current_tag, available_tags, expected_tag):
    latest_tag = dfetch.util.versions.latest_tag_from_list(current_tag, available_tags)

    assert expected_tag == latest_tag
