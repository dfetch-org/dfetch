"""Test the Version object command."""
# mypy: ignore-errors
# flake8: noqa

import pytest

from dfetch.manifest.version import Version


@pytest.mark.parametrize(
    "name, version_1, version_2, expected_equality",
    [
        (
            "both-empty",
            Version(),
            Version(),
            True,
        ),
        (
            "other-none",
            Version(),
            None,
            False,
        ),
        (
            "tag-only-equal",
            Version(tag="0.2"),
            Version(tag="0.2"),
            True,
        ),
        (
            "tag-only-unequal",
            Version(tag="0.2"),
            Version(tag="0.3"),
            False,
        ),
        (
            "tag-and-other-branch-unequal",
            Version(tag="0.2"),
            Version(tag="0.3", branch="main"),
            False,
        ),
        (
            "tag-and-other-branch-equal",
            Version(tag="0.2"),
            Version(tag="0.2", branch="main"),
            True,
        ),
        (
            "tag-and-self-branch-unequal",
            Version(tag="0.3", branch="main"),
            Version(tag="0.2"),
            False,
        ),
        (
            "tag-and-self-branch-equal",
            Version(tag="0.2", branch="main"),
            Version(tag="0.2"),
            True,
        ),
        (
            "tag-and-other-revision-unequal",
            Version(tag="0.2"),
            Version(tag="0.3", revision="123"),
            False,
        ),
        (
            "tag-and-other-revision-equal",
            Version(tag="0.2"),
            Version(tag="0.2", revision="123"),
            True,
        ),
        (
            "tag-and-self-revision-unequal",
            Version(tag="0.3", revision="123"),
            Version(tag="0.2"),
            False,
        ),
        (
            "tag-and-self-revision-equal",
            Version(tag="0.2", revision="123"),
            Version(tag="0.2"),
            True,
        ),
        (
            "tag-and-self-revision-other-branch-unequal",
            Version(tag="0.3", revision="123"),
            Version(tag="0.2", branch="main"),
            False,
        ),
        (
            "tag-and-self-revision-other-branch-equal",
            Version(tag="0.2", revision="123"),
            Version(tag="0.2", branch="main"),
            True,
        ),
        (
            "tag-and-other-revision-self-branch-unequal",
            Version(tag="0.2", branch="main"),
            Version(tag="0.3", revision="123"),
            False,
        ),
        (
            "tag-and-other-revision-self-branch-equal",
            Version(tag="0.2", branch="main"),
            Version(tag="0.2", revision="123"),
            True,
        ),
        (
            "tag-and-other-revision-branch-unequal",
            Version(tag="0.2"),
            Version(tag="0.3", revision="123", branch="main"),
            False,
        ),
        (
            "tag-and-other-revision-branch-equal",
            Version(tag="0.2"),
            Version(tag="0.2", revision="123", branch="main"),
            True,
        ),
        (
            "tag-and-self-revision-branch-unequal",
            Version(tag="0.3", revision="123", branch="main"),
            Version(tag="0.2"),
            False,
        ),
        (
            "tag-and-self-revision-branch-equal",
            Version(tag="0.2", revision="123", branch="main"),
            Version(tag="0.2"),
            True,
        ),
        (
            "tag-and-both-revision-branch-but-tag-unequal",
            Version(tag="0.2", revision="123", branch="main"),
            Version(tag="0.3", revision="123", branch="main"),
            False,
        ),
        (
            "tag-and-both-revision-branch-and-tag-equal",
            Version(tag="0.2", revision="123", branch="main"),
            Version(tag="0.2", revision="123", branch="main"),
            True,
        ),
        (
            "tag-and-both-revision-branch-tag-equal-revision-unequal",
            Version(tag="0.2", revision="456", branch="main"),
            Version(tag="0.2", revision="123", branch="main"),
            True,
        ),
        (
            "both-revision-branch-revision-unequal",
            Version(revision="456", branch="main"),
            Version(revision="123", branch="main"),
            False,
        ),
        (
            "both-revision-branch-revision-equal",
            Version(revision="123", branch="main"),
            Version(revision="123", branch="main"),
            True,
        ),
        (
            "both-revision-branch-branch-unequal",
            Version(revision="123", branch="main"),
            Version(revision="123", branch="develop"),
            False,
        ),
        (
            "both-revision-branch-branch-equal",
            Version(revision="123", branch="main"),
            Version(revision="123", branch="main"),
            True,
        ),
        (
            "revision-only-unequal",
            Version(revision="123"),
            Version(revision="456"),
            False,
        ),
        (
            "revision-only-equal",
            Version(revision="123"),
            Version(revision="123"),
            True,
        ),
        (
            "branch-only-unequal",
            Version(branch="main"),
            Version(branch="develop"),
            False,
        ),
        (
            "branch-only-equal",
            Version(branch="main"),
            Version(branch="main"),
            True,
        ),
    ],
)
def test_version_comparison(name, version_1, version_2, expected_equality):
    actual_equality = version_1 == version_2
    assert actual_equality == expected_equality
