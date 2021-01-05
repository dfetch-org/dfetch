"""Test the manifest."""
# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import mock_open, patch

import pytest

import dfetch.manifest.manifest
from dfetch.manifest.manifest import Manifest, find_manifest
from dfetch import DEFAULT_MANIFEST_NAME

BASIC_MANIFEST = u"""
manifest:
   version: 0

   remotes:
   - name: my-remote
     url-base: "http://www.myremote.com/"

   projects:
   - name: my-project
"""

MANIFEST_NO_PROJECTS = u"""
manifest:
   version: 0

   remotes:
   - name: my-remote
     url-base: "http://www.myremote.com/"
"""

DICTIONARY_MANIFEST = {
    "version": 0,
    "remotes": [{"name": "my-remote", "url-base": "http://www.myremote.com/"}],
    "projects": [{"name": "my-project"}],
}


def given_manifest_from_text(text: str) -> Manifest:
    """Given the manifest as specified."""
    with patch("dfetch.manifest.manifest.open", mock_open(read_data=text)):
        return Manifest.from_file(DEFAULT_MANIFEST_NAME)


def test_can_read_version() -> None:
    """Test that the version can be read."""
    manifest = given_manifest_from_text(BASIC_MANIFEST)
    assert manifest.version == 0


def test_no_projects() -> None:
    """Test that manifest without projects cannot be read."""

    with pytest.raises(KeyError):
        manifest = given_manifest_from_text(MANIFEST_NO_PROJECTS)


def test_construct_from_dict() -> None:
    """Test that manifest can be constructed from dictionary."""

    manifest = Manifest(DICTIONARY_MANIFEST)
    assert manifest.version == 0
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

        with pytest.raises(RuntimeError):
            find_manifest()


def test_single_manifest_found() -> None:

    with patch("dfetch.manifest.manifest.find_file") as find_file_mock:

        find_file_mock.return_value = [DEFAULT_MANIFEST_NAME]

        assert os.path.join(os.getcwd(), DEFAULT_MANIFEST_NAME) == find_manifest()
