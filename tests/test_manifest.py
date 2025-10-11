"""Test the manifest."""

# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import mock_open, patch

import pytest

from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.manifest.manifest import (
    Manifest,
    ManifestDict,
    ManifestEntryLocation,
    RequestedProjectNotFoundError,
    find_manifest,
    get_childmanifests,
)
from dfetch.manifest.project import ProjectEntry

BASIC_MANIFEST = """
manifest:
   version: 0

   remotes:
   - name: my-remote
     url-base: "http://www.myremote.com/"

   projects:
   - name: my-project
"""

MANIFEST_NO_PROJECTS = """
manifest:
   version: 0

   remotes:
   - name: my-remote
     url-base: "http://www.myremote.com/"
"""


MANIFEST_NO_REMOTES = """
manifest:
   version: 0

   projects:
   - name: my-project
     url: "http://www.somewhere.com"
"""

DICTIONARY_MANIFEST = ManifestDict(
    version="0",
    remotes=[{"name": "my-remote", "url-base": "http://www.myremote.com/"}],
    projects=[{"name": "my-project"}],
)


def given_manifest_from_text(text: str) -> Manifest:
    """Given the manifest as specified."""
    with patch("dfetch.manifest.manifest.open", mock_open(read_data=text)):
        return Manifest.from_file(DEFAULT_MANIFEST_NAME)


def test_can_read_version() -> None:
    """Test that the version can be read."""
    manifest = given_manifest_from_text(BASIC_MANIFEST)
    assert manifest.version == "0"


def test_no_projects() -> None:
    """Test that manifest without projects cannot be read."""

    with pytest.raises(KeyError):
        given_manifest_from_text(MANIFEST_NO_PROJECTS)


def test_no_remotes() -> None:
    """Test that manifest without remotes can be read."""

    manifest = given_manifest_from_text(MANIFEST_NO_REMOTES)

    assert len(manifest.projects) == 1
    assert manifest.projects[0].name == "my-project"
    assert manifest.projects[0].remote_url == "http://www.somewhere.com"
    assert len(manifest._remotes) == 0


def test_construct_from_dict() -> None:
    """Test that manifest can be constructed from dictionary."""

    manifest = Manifest(DICTIONARY_MANIFEST)
    assert manifest.version == "0"
    assert len(manifest.projects) == 1
    assert manifest.projects[0].name == "my-project"
    assert len(manifest._remotes) == 1
    assert next(iter(manifest._remotes.values())).name == "my-remote"


def test_no_manifests_found() -> None:
    with patch("dfetch.manifest.manifest.find_file"):
        with pytest.raises(RuntimeError):
            find_manifest()


def test_multiple_manifests_found() -> None:
    with patch("dfetch.manifest.manifest.find_file") as find_file_mock:
        find_file_mock.return_value = [DEFAULT_MANIFEST_NAME, "manifest2.yaml"]

        assert os.path.realpath(DEFAULT_MANIFEST_NAME) == find_manifest()


def test_single_manifest_found() -> None:
    with patch("dfetch.manifest.manifest.find_file") as find_file_mock:
        find_file_mock.return_value = [DEFAULT_MANIFEST_NAME]

        joined = os.path.realpath(os.path.join(os.getcwd(), DEFAULT_MANIFEST_NAME))
        found = find_manifest()
        assert joined == found


@pytest.mark.parametrize(
    "name, manifest_paths",
    [
        (
            "no-childmanifests",
            [],
        ),
        (
            "single-childmanifest",
            ["some-manifest.yaml"],
        ),
        (
            "multi-childmanifests",
            ["some-manifest.yaml", "some-other-manifest.yaml"],
        ),
    ],
)
def test_get_childmanifests(name, manifest_paths) -> None:
    parent = ProjectEntry({"name": "name"})

    with patch("dfetch.manifest.manifest.find_file") as find_file_mock:
        with patch("dfetch.manifest.manifest.validate"):
            with patch("dfetch.manifest.manifest.Manifest") as manifest_mock:
                find_file_mock.return_value = manifest_paths

                found_childmanifests = get_childmanifests([parent.name])

                assert len(found_childmanifests) == len(manifest_paths)

                for path, call in zip(
                    manifest_paths,
                    manifest_mock.from_file.call_args_list,  # , strict=True
                ):
                    assert os.path.realpath(path) == call[0][0]


def test_suggestion_found() -> None:
    exception = RequestedProjectNotFoundError(["fIrst"], ["first", "other"])

    assert ["first"] == exception._guess_project(["fIrst"])


def test_suggestion_not_found() -> None:
    exception = RequestedProjectNotFoundError(["1234"], ["first", "other"])

    assert [] == exception._guess_project(["1234"])


def test_multiple_suggestions_found() -> None:
    exception = RequestedProjectNotFoundError(["irst", "otheR"], ["first", "other"])

    assert ["first", "other"] == exception._guess_project(["irst", "otheR"])


def test_single_suggestion_not_found() -> None:
    exception = RequestedProjectNotFoundError(["irst", "1234"], ["first", "other"])

    assert ["first"] == exception._guess_project(["irst", "1234"])


@pytest.mark.parametrize(
    "name, manifest, project_name, result",
    [
        (
            "match",
            " - name: foo",
            "foo",
            ManifestEntryLocation(line_number=1, start=10, end=12),
        ),
        (
            "no match",
            " - name: foo",
            "baz",
            RuntimeError,
        ),
        (
            "with comment",
            " - name: foo # some comment",
            "foo",
            ManifestEntryLocation(line_number=1, start=10, end=12),
        ),
        (
            "no spaces",
            " -name:foo #some comment",
            "foo",
            ManifestEntryLocation(line_number=1, start=8, end=10),
        ),
    ],
)
def test_get_manifest_location(name, manifest, project_name, result) -> None:

    manifest = Manifest(DICTIONARY_MANIFEST, text=manifest)

    if result == RuntimeError:
        with pytest.raises(RuntimeError):
            manifest.find_name_in_manifest(project_name)
    else:
        assert manifest.find_name_in_manifest(project_name) == result
