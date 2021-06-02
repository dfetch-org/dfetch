"""Test the Version object command."""
# mypy: ignore-errors
# flake8: noqa

import pytest

from dfetch.manifest.project import ProjectEntry


def test_projectentry_name():
    assert ProjectEntry({"name": "SomeProject"}).name == "SomeProject"


def test_projectentry_revision():
    assert ProjectEntry({"name": "SomeProject", "revision": "123"}).revision == "123"


def test_projectentry_remote():
    assert (
        ProjectEntry({"name": "SomeProject", "remote": "SomeRemote"}).remote
        == "SomeRemote"
    )


def test_projectentry_source():
    assert ProjectEntry({"name": "SomeProject", "src": "SomePath"}).source == "SomePath"


def test_projectentry_vcs():
    assert ProjectEntry({"name": "SomeProject", "vcs": "git"}).vcs == "git"


def test_projectentry_patch():
    assert (
        ProjectEntry({"name": "SomeProject", "patch": "diff.patch"}).patch
        == "diff.patch"
    )


def test_projectentry_as_yaml():
    assert ProjectEntry({"name": "SomeProject"}).as_yaml() == {"name": "SomeProject"}


def test_projectentry_as_str():
    assert (
        str(ProjectEntry({"name": "SomeProject"}))
        == "SomeProject          latest  SomeProject"
    )
