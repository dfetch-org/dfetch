"""Test the subproject class."""

# mypy: ignore-errors
# flake8: noqa

from contextlib import ExitStack
from typing import Optional, Union
from unittest.mock import MagicMock, patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.fetcher import AbstractVcsFetcher
from dfetch.project.metadata import Dependency
from dfetch.project.subproject import SubProject
from dfetch.vcs.patch import PatchType


class MockVcsFetcher(AbstractVcsFetcher):
    """Minimal concrete VCS fetcher for unit tests."""

    NAME: str = "mock"

    def __init__(self, wanted: Version | None = None) -> None:
        self._wanted = wanted or Version()

    @classmethod
    def handles(cls, remote: str) -> bool:
        return False

    def revision_is_enough(self) -> bool:
        return False

    def get_default_branch(self) -> str:
        return ""

    def list_of_tags(self) -> list[str]:
        return []

    def list_of_branches(self) -> list[str]:
        return []

    def latest_revision_on_branch(self, branch: str) -> str:
        return "latest"

    def does_revision_exist(self, revision: str) -> bool:
        return True

    def browse_tree(self, version: str) -> object:
        return None

    def patch_type(self) -> PatchType:
        return PatchType.GIT

    def fetch(
        self, version, local_path, name, source, ignore
    ) -> tuple[Version, list[Dependency]]:
        return version, []

    def wanted_version(self, project_entry: ProjectEntry) -> Version:
        return self._wanted

    @staticmethod
    def list_tool_info() -> None:
        pass


def _make_subproject(
    name: str = "proj1", wanted: Version | None = None
) -> tuple[SubProject, MockVcsFetcher]:
    fetcher = MockVcsFetcher(wanted)
    return SubProject(ProjectEntry({"name": name}), fetcher), fetcher


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
    given_on_disk: Union[Version, None],
    given_wanted: Version,
    expect_wanted: Version,
    expect_have: Union[Version, None],
):
    with patch("dfetch.project.subproject.os.path.exists") as mocked_path_exists:
        with patch("dfetch.project.subproject.Metadata.from_file") as mocked_metadata:
            subproject, _ = _make_subproject(wanted=given_wanted)

            mocked_path_exists.return_value = bool(given_on_disk)
            mocked_metadata().version = given_on_disk

            wanted, have = subproject.check_wanted_with_local()

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
    with patch("dfetch.project.subproject.hash_directory") as mocked_hash_directory:
        with patch(
            "dfetch.project.subproject.SubProject._on_disk_hash"
        ) as mocked_on_disk_hash:
            subproject, _ = _make_subproject()

            mocked_on_disk_hash.return_value = hash_in_metadata
            mocked_hash_directory.return_value = current_hash

            assert expectation == subproject._are_there_local_changes(
                files_to_ignore=[]
            )


def test_update_uses_ignored_files_callback_for_stored_hash():
    """The hash stored after fetch must use the post-fetch ignored files.

    The callback is called twice: once before clearing (pre-fetch local-changes
    check) and once after extraction (to compute the stored hash).  The second
    call returns the post-extraction state so the stored hash matches what
    dfetch check will compute later.
    """
    pre_fetch_ignored = ["old_file.txt"]
    post_fetch_ignored = ["new_ignored.txt"]

    # Return different values on successive calls to simulate pre/post extraction
    callback = MagicMock(side_effect=[pre_fetch_ignored, post_fetch_ignored])

    with ExitStack() as stack:
        mock_exists = stack.enter_context(
            patch("dfetch.project.subproject.os.path.exists")
        )
        mock_meta_file = stack.enter_context(
            patch("dfetch.project.subproject.Metadata.from_file")
        )
        mock_hash = stack.enter_context(
            patch("dfetch.project.subproject.hash_directory")
        )
        stack.enter_context(patch("dfetch.project.subproject.safe_rm"))
        stack.enter_context(patch("dfetch.project.metadata.Metadata.fetched"))
        stack.enter_context(patch("dfetch.project.metadata.Metadata.dump"))

        mock_exists.return_value = True
        mock_meta_file.return_value.version = Version(revision="abc")
        mock_meta_file.return_value.hash = None
        mock_hash.return_value = "hash123"

        subproject, _ = _make_subproject(name="p1", wanted=Version(revision="new"))

        subproject.update(force=True, ignored_files_callback=callback)

        assert callback.call_count == 2
        # The hash must be computed with the post-fetch ignored list
        hash_call_skiplist = mock_hash.call_args[1]["skiplist"]
        assert "new_ignored.txt" in hash_call_skiplist
        assert "old_file.txt" not in hash_call_skiplist


@pytest.mark.parametrize(
    "name, project_version, on_disk_version, expect_return, expect_project_version",
    [
        (
            "already-pinned-tag-matches",
            Version(tag="v1.0", branch="main"),
            Version(tag="v1.0", branch="main"),
            None,
            Version(tag="v1.0", branch="main"),
        ),
        (
            "already-pinned-tag-matches-branch-differs",
            Version(tag="v1.0"),
            Version(tag="v1.0", branch="main"),
            None,
            Version(tag="v1.0"),
        ),
        (
            "already-pinned-revision-matches-branch-differs",
            Version(revision="abc123"),
            Version(revision="abc123", branch="feature"),
            "abc123",
            Version(revision="abc123", branch="feature"),
        ),
        (
            "tag-differs-triggers-freeze",
            Version(tag="v1.0"),
            Version(tag="v2.0", branch="main"),
            "v2.0",
            Version(tag="v2.0", branch="main"),
        ),
        (
            "revision-differs-triggers-freeze",
            Version(revision="abc123"),
            Version(revision="def456", branch="main"),
            "def456",
            Version(revision="def456", branch="main"),
        ),
        (
            "no-on-disk-version",
            Version(tag="v1.0"),
            None,
            None,
            Version(tag="v1.0"),
        ),
    ],
)
def test_freeze_project(
    name: str,
    project_version: Version,
    on_disk_version: Union[Version, None],
    expect_return: Union[str, None],
    expect_project_version: Version,
):
    with patch("dfetch.project.subproject.os.path.exists") as mocked_path_exists:
        with patch("dfetch.project.subproject.Metadata.from_file") as mocked_metadata:
            subproject, _ = _make_subproject()

            mocked_path_exists.return_value = bool(on_disk_version)
            mocked_metadata().version = on_disk_version

            project = ProjectEntry({"name": "proj1"})
            project.version = project_version

            result = subproject.freeze_project(project)

            assert result == expect_return
            assert project.version == expect_project_version


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

    assert SubProject._running_in_ci() == expected_result
