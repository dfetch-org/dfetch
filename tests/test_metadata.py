"""Test metadata loading."""

# mypy: ignore-errors
# flake8: noqa

import textwrap

import pytest

from dfetch.project.metadata import InvalidMetadataError, Metadata

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
