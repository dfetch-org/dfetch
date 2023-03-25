"""Test the check command."""
# mypy: ignore-errors
# flake8: noqa

import pytest
from semver import VersionInfo

import dfetch.util.versions


@pytest.mark.parametrize(
    "name, tag_string, expected_version, expected_prefix, expected_rest",
    [
        (
            "prefix",
            "module/1.2.3",
            VersionInfo(major=1, minor=2, patch=3),
            "module/",
            "",
        ),
        (
            "prefix-lower-v",
            "module/v1.2.3",
            VersionInfo(major=1, minor=2, patch=3),
            "module/",
            "",
        ),
        (
            "prefix-upper-v",
            "module/V1.2.3",
            VersionInfo(major=1, minor=2, patch=3),
            "module/",
            "",
        ),
        (
            "prefix-multi-v",
            "vvV1.2.3",
            VersionInfo(major=1, minor=2, patch=3),
            "vv",
            "",
        ),
        (
            "prefix-multi-versions",
            "v1.2.3-v2.3.4",
            VersionInfo(major=1, minor=2, patch=3),
            "",
            "-v2.3.4",
        ),
        ("empty", "", VersionInfo(major=0, minor=0, patch=0), "", ""),
        ("only-major-minor", "1.2", VersionInfo(major=1, minor=2, patch=0), "", ""),
        (
            "only-major-minor-lower-v",
            "v1.2",
            VersionInfo(major=1, minor=2, patch=0),
            "",
            "",
        ),
        (
            "only-major-minor-upper-v",
            "V1.2",
            VersionInfo(major=1, minor=2, patch=0),
            "",
            "",
        ),
        ("only-major-lower-v", "v1", VersionInfo(major=1, minor=0, patch=0), "", ""),
        ("only-major-upper-v", "V1", VersionInfo(major=1, minor=0, patch=0), "", ""),
        ("only-major", "1", VersionInfo(major=1, minor=0, patch=0), "", ""),
        ("only-major", "1", VersionInfo(major=1, minor=0, patch=0), "", ""),
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
