"""Test the Version object command."""

# mypy: ignore-errors
# flake8: noqa

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


def test_remote_url_ssh_shorthand_uses_colon_separator():
    entry = ProjectEntry({"name": "myrepo", "repo-path": "myorg/myrepo.git"})
    entry.set_remote(Remote({"name": "corp", "url-base": "git@git.mycompany.com"}))
    assert entry.remote_url == "git@git.mycompany.com:myorg/myrepo.git"


def test_remote_url_https_base_uses_slash_separator():
    entry = ProjectEntry({"name": "myrepo", "repo-path": "myorg/myrepo"})
    entry.set_remote(Remote({"name": "corp", "url-base": "https://github.com"}))
    assert entry.remote_url == "https://github.com/myorg/myrepo"


def test_set_remote_strips_colon_prefix_from_ssh_url():
    entry = ProjectEntry({"name": "myrepo", "url": "git@git.mycompany.com:my-repo.git"})
    entry.set_remote(Remote({"name": "corp", "url-base": "git@git.mycompany.com"}))
    assert entry.remote_url == "git@git.mycompany.com:my-repo.git"


def test_set_remote_strips_slash_prefix_from_https_url():
    entry = ProjectEntry({"name": "myrepo", "url": "https://github.com/org/repo"})
    entry.set_remote(Remote({"name": "gh", "url-base": "https://github.com"}))
    assert entry.remote_url == "https://github.com/org/repo"


def test_remote_url_with_trailing_slash_in_base():
    entry = ProjectEntry({"name": "myrepo", "repo-path": "myorg/myrepo"})
    entry.set_remote(Remote({"name": "corp", "url-base": "https://github.com/"}))
    assert entry.remote_url == "https://github.com/myorg/myrepo"


def test_remote_url_with_empty_repo_path():
    entry = ProjectEntry({"name": "myrepo"})
    entry.set_remote(Remote({"name": "corp", "url-base": "git@git.mycompany.com"}))
    assert entry.remote_url == "git@git.mycompany.com"
