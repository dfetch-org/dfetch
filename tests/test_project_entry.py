"""Test the Version object command."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import Mock

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.remote import Remote


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
    assert ProjectEntry({"name": "SomeProject", "patch": "diff.patch"}).patch == [
        "diff.patch"
    ]
    assert ProjectEntry({"name": "SomeProject", "patch": ["diff.patch"]}).patch == [
        "diff.patch"
    ]


def test_projectentry_as_yaml():
    assert ProjectEntry({"name": "SomeProject"}).as_yaml() == {"name": "SomeProject"}


def test_projectentry_as_str():
    assert (
        str(ProjectEntry({"name": "SomeProject"}))
        == "SomeProject          latest  SomeProject"
    )


def test_set_remote_strips_only_leading_prefix():
    """set_remote must remove only the leading remote URL, not every occurrence."""
    remote = Mock(spec=Remote)
    remote.name = "r"
    remote.url = "https://host/org"

    # The repo path repeats the remote base; only the leading prefix may be removed.
    entry = ProjectEntry({"name": "p", "url": "https://host/org/https://host/org/sub"})
    entry.set_remote(remote)

    assert entry.remote_url == "https://host/org/https://host/org/sub"
