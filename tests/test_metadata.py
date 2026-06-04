"""Test metadata loading."""

# mypy: ignore-errors
# flake8: noqa

import textwrap

import pytest
import yaml

from dfetch.project.metadata import InvalidMetadataError, Metadata, _strip_userinfo

VALID_METADATA = """\
    dfetch:
      remote_url: https://example.com/repo
      branch: main
      tag: ''
      revision: abc123
      last_fetch: 01/01/2000, 00:00:00
      hash: deadbeef
      patch: ''
    """


def _write_metadata(tmp_path, content):
    path = tmp_path / ".dfetch_data.yaml"
    path.write_text(textwrap.dedent(content))
    return str(path)


def test_from_file_raises_when_dfetch_value_is_a_scalar(tmp_path):
    """A scalar under 'dfetch:' must raise InvalidMetadataError, not AttributeError."""
    path = _write_metadata(tmp_path, "dfetch: just-a-string\n")
    with pytest.raises(InvalidMetadataError):
        Metadata.from_file(path)


def test_from_file_raises_when_dfetch_value_is_a_list(tmp_path):
    """A list under 'dfetch:' must raise InvalidMetadataError, not AttributeError."""
    path = _write_metadata(tmp_path, "dfetch:\n  - item1\n  - item2\n")
    with pytest.raises(InvalidMetadataError):
        Metadata.from_file(path)


def test_from_file_raises_when_dfetch_value_is_null(tmp_path):
    """A null under 'dfetch:' must raise InvalidMetadataError, not AttributeError."""
    path = _write_metadata(tmp_path, "dfetch:\n")
    with pytest.raises(InvalidMetadataError):
        Metadata.from_file(path)


def test_from_file_raises_on_invalid_yaml_syntax(tmp_path):
    """Broken YAML syntax must raise InvalidMetadataError."""
    path = _write_metadata(tmp_path, "dfetch: [unclosed bracket\n")
    with pytest.raises(InvalidMetadataError):
        Metadata.from_file(path)


def test_from_file_raises_when_dfetch_key_is_absent(tmp_path):
    """A file with no 'dfetch' top-level key must raise InvalidMetadataError."""
    path = _write_metadata(tmp_path, "other_key: value\n")
    with pytest.raises(InvalidMetadataError):
        Metadata.from_file(path)


def test_from_file_loads_remote_url(tmp_path):
    """remote_url is read back correctly from a valid file."""
    path = _write_metadata(tmp_path, VALID_METADATA)
    meta = Metadata.from_file(path)
    assert meta.remote_url == "https://example.com/repo"


def test_from_file_loads_branch(tmp_path):
    """branch is read back correctly from a valid file."""
    path = _write_metadata(tmp_path, VALID_METADATA)
    meta = Metadata.from_file(path)
    assert meta.branch == "main"


def test_from_file_loads_revision(tmp_path):
    """revision is read back correctly from a valid file."""
    path = _write_metadata(tmp_path, VALID_METADATA)
    meta = Metadata.from_file(path)
    assert meta.revision == "abc123"


def test_from_file_loads_hash(tmp_path):
    """hash is read back correctly from a valid file."""
    path = _write_metadata(tmp_path, VALID_METADATA)
    meta = Metadata.from_file(path)
    assert meta.hash == "deadbeef"


def test_from_file_uses_defaults_for_missing_fields(tmp_path):
    """A minimal mapping with only the 'dfetch' key and no fields uses defaults."""
    path = _write_metadata(tmp_path, "dfetch: {}\n")
    meta = Metadata.from_file(path)
    assert meta.remote_url == ""
    assert meta.branch == ""
    assert meta.revision == ""
    assert meta.hash == ""
    assert meta.patch == []
    assert meta.dependencies == []


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://user:token@github.com/org/repo.git",
         "https://github.com/org/repo.git"),
        ("https://user@github.com/org/repo.git",
         "https://github.com/org/repo.git"),
        ("https://github.com/org/repo.git",
         "https://github.com/org/repo.git"),
        ("https://user:tok@github.com:8443/org/repo.git",
         "https://github.com:8443/org/repo.git"),
        ("https://example.com/archive.tar.gz?token=keep&v=1",
         "https://example.com/archive.tar.gz?token=keep&v=1"),
        ("file:///local/path/repo",
         "file:///local/path/repo"),
        ("", ""),
        ("/just/a/path", "/just/a/path"),
        # IPv6 literals: brackets must be preserved when reconstructing netloc.
        ("https://user:tok@[::1]:8080/x",
         "https://[::1]:8080/x"),
        ("https://[fe80::1]/x",
         "https://[fe80::1]/x"),
    ],
)
def test_strip_userinfo_redacts_credentials(url, expected):
    """_strip_userinfo removes userinfo, preserves scheme/host/port/path/query."""
    assert _strip_userinfo(url) == expected


def _dump_metadata(tmp_path, *, remote_url, dependencies=None):
    """Build a Metadata pointing at *tmp_path* and dump it; return the YAML payload."""
    meta = Metadata(
        {
            "remote_url": remote_url,
            "branch": "main",
            "revision": "abc123",
            "hash": "deadbeef",
            "destination": str(tmp_path),
            "dependencies": dependencies or [],
        }
    )
    meta.dump()
    with open(meta.path, encoding="utf-8") as fh:
        return fh.read(), meta.path


def test_dump_strips_credentials_from_remote_url(tmp_path):
    """Metadata.dump redacts userinfo from remote_url on disk."""
    raw, path = _dump_metadata(
        tmp_path, remote_url="https://alice:secret-token@example.com/org/repo.git"
    )
    assert "alice" not in raw
    assert "secret-token" not in raw
    assert "@example.com" not in raw
    assert "https://example.com/org/repo.git" in raw
    # Round-trip survives Metadata.from_file.
    reloaded = Metadata.from_file(path)
    assert reloaded.remote_url == "https://example.com/org/repo.git"


def test_dump_strips_credentials_from_dependency_remote_url(tmp_path):
    """Metadata.dump redacts userinfo from each dependencies[].remote_url."""
    dep = {
        "branch": "",
        "tag": "",
        "revision": "f00",
        "remote_url": "https://bob:pat@gitlab.com/grp/sub.git",
        "destination": "vendor/sub",
        "source_type": "git-submodule",
    }
    raw, path = _dump_metadata(
        tmp_path,
        remote_url="https://example.com/org/repo.git",
        dependencies=[dep],
    )
    assert "bob" not in raw
    assert "bob:pat@" not in raw
    assert "@gitlab.com" not in raw
    parsed = yaml.safe_load(raw)
    assert (
        parsed["dfetch"]["dependencies"][0]["remote_url"]
        == "https://gitlab.com/grp/sub.git"
    )


def test_dump_leaves_in_memory_remote_url_untouched(tmp_path):
    """Redaction applies only to the on-disk representation."""
    meta = Metadata(
        {
            "remote_url": "https://carol:hunter2@example.com/org/repo.git",
            "destination": str(tmp_path),
        }
    )
    meta.dump()
    assert meta.remote_url == "https://carol:hunter2@example.com/org/repo.git"
