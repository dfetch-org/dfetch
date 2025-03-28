"""Test the vcs class."""

# mypy: ignore-errors
# flake8: noqa

from typing import Optional
from unittest.mock import patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.vcs import VCS


class ConcreteVCS(VCS):
    _wanted_version: Version

    def _fetch_impl(self, version: Version) -> Version:
        return Version()

    def _latest_revision_on_branch(self, branch):
        return "latest"

    def check(self):
        return False

    @staticmethod
    def list_tool_info():
        pass

    @staticmethod
    def revision_is_enough():
        return False

    def _does_revision_exist(self, revision):
        return True

    @property
    def wanted_version(self):
        return self._wanted_version

    def _list_of_tags(self):
        return []

    def current_revision(self):
        return "1"

    def metadata_revision(self):
        return "1"

    def get_diff(self, old_revision, new_revision):
        return ""

    def get_default_branch(self):
        return ""


@pytest.mark.parametrize(
    "name, given_on_disk, given_wanted, expect_wanted, expect_have",
    [
        (
            "tag-only",
            Version(tag="0.0.3"),
            Version(tag="0.0.4"),
            Version(tag="0.0.4"),
            Version(tag="0.0.3"),
        ),
        (
            "tag-with-rev-only",
            Version(tag="0.0.3", revision="123"),
            Version(tag="0.0.4", revision="123"),
            Version(tag="0.0.4"),
            Version(tag="0.0.3"),
        ),
        ("nothing-on-disk", None, Version(tag="0.0.4"), Version(tag="0.0.4"), None),
        (
            "rev-only",
            Version(revision="123"),
            Version(revision="124"),
            Version(revision="124"),
            Version(revision="123"),
        ),
        (
            "rev-and-branch",
            Version(revision="123", branch="a-branch"),
            Version(revision="124", branch="a-branch"),
            Version(revision="124", branch="a-branch"),
            Version(revision="123", branch="a-branch"),
        ),
        (
            "branch-only",
            Version(branch="a-branch"),
            Version(branch="a-branch"),
            Version(branch="a-branch", revision="latest"),
            Version(branch="a-branch"),
        ),
    ],
)
def test_check_wanted_with_local(
    name: str,
    given_on_disk: Version | None,
    given_wanted: Version,
    expect_wanted: Version,
    expect_have: Version | None,
):
    with patch("dfetch.project.vcs.os.path.exists") as mocked_path_exists:
        with patch("dfetch.project.vcs.Metadata.from_file") as mocked_metadata:
            vcs = ConcreteVCS(ProjectEntry({"name": "proj1"}))

            mocked_path_exists.return_value = bool(given_on_disk)
            mocked_metadata().version = given_on_disk

            vcs._wanted_version = given_wanted

            wanted, have = vcs.check_wanted_with_local()

            assert wanted == expect_wanted
            assert have == expect_have


@pytest.mark.parametrize(
    "name, hash_in_metadata, current_hash, expectation",
    [
        ("no-hash", "", "1234", False),
        ("different-hash", "5678", "1234", True),
        ("same-hash", "1234", "1234", False),
    ],
)
def test_are_there_local_changes(
    name: str, hash_in_metadata: str, current_hash: str, expectation: bool
):
    with patch("dfetch.project.vcs.hash_directory") as mocked_hash_directory:
        with patch("dfetch.project.vcs.VCS._on_disk_hash") as mocked_on_disk_hash:
            vcs = ConcreteVCS(ProjectEntry({"name": "proj1"}))

            mocked_on_disk_hash.return_value = hash_in_metadata
            mocked_hash_directory.return_value = current_hash

            assert expectation == vcs._are_there_local_changes()


@pytest.mark.parametrize(
    "ci_env_value, expected_result",
    [
        ("true", True),
        ("1", True),
        ("True", True),
        ("yes", True),
        ("YES", True),
        ("false", False),
        (None, False),
        (0, False),
        ("other", False),
    ],
)
def test_ci_enabled(
    monkeypatch: pytest.MonkeyPatch, ci_env_value: Optional[str], expected_result: bool
):
    if ci_env_value is None:
        monkeypatch.delenv("CI", raising=False)
    else:
        monkeypatch.setenv("CI", str(ci_env_value))

    assert ConcreteVCS._running_in_ci() == expected_result
