"""Unit tests for the Integrity dataclass and ProjectEntry integrity fields."""

from dfetch.manifest.project import Integrity, ProjectEntry


# ---------------------------------------------------------------------------
# Integrity dataclass
# ---------------------------------------------------------------------------


def test_integrity_empty_is_falsy():
    assert not Integrity()


def test_integrity_with_hash_is_truthy():
    assert Integrity(hash="sha256:" + "a" * 64)


def test_integrity_as_yaml_empty():
    assert Integrity().as_yaml() == {}


def test_integrity_as_yaml_with_hash():
    h = "sha256:" + "a" * 64
    assert Integrity(hash=h).as_yaml() == {"hash": h}


# ---------------------------------------------------------------------------
# ProjectEntry with integrity block
# ---------------------------------------------------------------------------


def test_projectentry_hash_from_integrity_block():
    h = "sha256:" + "b" * 64
    project = ProjectEntry({"name": "lib", "integrity": {"hash": h}})
    assert project.hash == h


def test_projectentry_hash_empty_by_default():
    project = ProjectEntry({"name": "lib"})
    assert project.hash == ""


def test_projectentry_integrity_truthy_with_hash():
    h = "sha256:" + "c" * 64
    project = ProjectEntry({"name": "lib", "integrity": {"hash": h}})
    assert project.integrity


def test_projectentry_integrity_falsy_without_hash():
    project = ProjectEntry({"name": "lib", "integrity": {}})
    assert not project.integrity


def test_projectentry_as_yaml_includes_integrity():
    h = "sha256:" + "d" * 64
    project = ProjectEntry({"name": "lib", "url": "https://example.com/lib.tar.gz", "vcs": "archive", "integrity": {"hash": h}})
    yaml_data = project.as_yaml()
    assert yaml_data["integrity"] == {"hash": h}


def test_projectentry_as_yaml_omits_empty_integrity():
    project = ProjectEntry({"name": "lib"})
    yaml_data = project.as_yaml()
    assert "integrity" not in yaml_data


def test_projectentry_hash_setter():
    project = ProjectEntry({"name": "lib", "url": "https://example.com/lib.tar.gz", "vcs": "archive"})
    h = "sha256:" + "e" * 64
    project.hash = h
    assert project.hash == h
    assert project.integrity.hash == h
