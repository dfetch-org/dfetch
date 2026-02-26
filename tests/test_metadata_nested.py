"""Test metadata with nested projects support."""

# mypy: ignore-errors
# flake8: noqa

import datetime
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.metadata import DONT_EDIT_WARNING, Metadata, Options


class TestMetadataOptions:
    """Tests for Options TypedDict."""

    def test_options_creation_complete(self):
        """Test creating Options with all fields."""
        options: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "main",
            "tag": "v1.0.0",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": ["patch1.txt", "patch2.txt"],
            "nested": [],
        }

        assert options["branch"] == "main"
        assert options["tag"] == "v1.0.0"
        assert options["nested"] == []
        assert isinstance(options["patch"], list)

    def test_options_creation_minimal(self):
        """Test creating Options with minimal fields."""
        options: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "",
            "tag": "",
            "revision": "",
            "remote_url": "",
            "destination": "",
            "hash": "",
            "patch": "",
            "nested": [],
        }

        assert options["nested"] == []


class TestMetadataNested:
    """Tests for nested projects in Metadata."""

    def test_metadata_creation_with_nested(self):
        """Test creating metadata with nested projects."""
        nested_options: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "feature",
            "tag": "",
            "revision": "def456",
            "remote_url": "https://example.com/nested.git",
            "destination": "ext/nested",
            "hash": "nestedhash",
            "patch": [],
            "nested": [],
        }

        main_options: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 12, 30, 0),
            "branch": "main",
            "tag": "",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": ["patch.txt"],
            "nested": [nested_options],
        }

        metadata = Metadata(main_options)

        assert metadata.nested == [nested_options]
        assert len(metadata.nested) == 1
        assert metadata.nested[0]["remote_url"] == "https://example.com/nested.git"
        assert metadata.nested[0]["destination"] == "ext/nested"

    def test_metadata_creation_without_nested(self):
        """Test creating metadata without nested projects."""
        options: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "main",
            "tag": "",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": [],
            "nested": [],
        }

        metadata = Metadata(options)

        assert metadata.nested == []

    def test_metadata_fetched_with_nested(self):
        """Test updating metadata with nested projects."""
        options: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "main",
            "tag": "",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": [],
            "nested": [],
        }

        metadata = Metadata(options)

        nested_options: Options = {
            "last_fetch": datetime.datetime(2026, 1, 2, 0, 0, 0),
            "branch": "dev",
            "tag": "v2.0",
            "revision": "xyz789",
            "remote_url": "https://example.com/nested2.git",
            "destination": "ext/sub",
            "hash": "subhash",
            "patch": [],
            "nested": [],
        }

        new_version = Version(branch="main", revision="newrev123")
        metadata.fetched(
            version=new_version,
            hash_="newhash",
            patch_=["newpatch.txt"],
            nested=[nested_options],
        )

        assert metadata.nested == [nested_options]
        assert len(metadata.nested) == 1
        assert metadata.revision == "newrev123"
        assert metadata.patch == ["newpatch.txt"]

    def test_metadata_equality_with_nested(self):
        """Test metadata equality comparison with nested projects."""
        nested1: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "branch1",
            "tag": "",
            "revision": "rev1",
            "remote_url": "url1",
            "destination": "dest1",
            "hash": "hash1",
            "patch": [],
            "nested": [],
        }

        options1: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "main",
            "tag": "",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": [],
            "nested": [nested1],
        }

        options2: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "main",
            "tag": "",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": [],
            "nested": [nested1],
        }

        metadata1 = Metadata(options1)
        metadata2 = Metadata(options2)

        assert metadata1 == metadata2

    def test_metadata_inequality_with_different_nested(self):
        """Test metadata inequality when nested projects differ."""
        nested1: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "branch1",
            "tag": "",
            "revision": "rev1",
            "remote_url": "url1",
            "destination": "dest1",
            "hash": "hash1",
            "patch": [],
            "nested": [],
        }

        nested2: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "branch2",
            "tag": "",
            "revision": "rev2",
            "remote_url": "url2",
            "destination": "dest2",
            "hash": "hash2",
            "patch": [],
            "nested": [],
        }

        options1: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "main",
            "tag": "",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": [],
            "nested": [nested1],
        }

        options2: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "main",
            "tag": "",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": [],
            "nested": [nested2],
        }

        metadata1 = Metadata(options1)
        metadata2 = Metadata(options2)

        assert metadata1 != metadata2


class TestMetadataDump:
    """Tests for dumping metadata with nested projects."""

    def test_dump_metadata_with_nested(self):
        """Test dumping metadata file with nested projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_options: Options = {
                "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
                "branch": "feature",
                "tag": "v1.0",
                "revision": "def456",
                "remote_url": "https://example.com/nested.git",
                "destination": "ext/nested",
                "hash": "nestedhash",
                "patch": ["nested.patch"],
                "nested": [],
            }

            options: Options = {
                "last_fetch": datetime.datetime(2026, 1, 1, 12, 30, 0),
                "branch": "main",
                "tag": "",
                "revision": "abc123",
                "remote_url": "https://example.com/repo.git",
                "destination": tmpdir,
                "hash": "hash123",
                "patch": ["main.patch"],
                "nested": [nested_options],
            }

            metadata = Metadata(options)
            metadata.dump()

            # Verify file was created
            metadata_file = os.path.join(tmpdir, Metadata.FILENAME)
            assert os.path.exists(metadata_file)

            # Read and verify content
            with open(metadata_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for warning
            assert DONT_EDIT_WARNING in content

            # Check for nested section
            assert "nested:" in content

    def test_dump_metadata_without_nested(self):
        """Test dumping metadata file without nested projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            options: Options = {
                "last_fetch": datetime.datetime(2026, 1, 1, 12, 30, 0),
                "branch": "main",
                "tag": "",
                "revision": "abc123",
                "remote_url": "https://example.com/repo.git",
                "destination": tmpdir,
                "hash": "hash123",
                "patch": [],
                "nested": [],
            }

            metadata = Metadata(options)
            metadata.dump()

            # Verify file was created
            metadata_file = os.path.join(tmpdir, Metadata.FILENAME)
            assert os.path.exists(metadata_file)

            # Read and verify content
            with open(metadata_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for warning
            assert DONT_EDIT_WARNING in content

            # Nested section should not be present when empty
            # (based on the code, it only adds nested if it exists)
            lines = content.split('\n')
            yaml_content = '\n'.join(line for line in lines if not line.strip().startswith('#'))

            # If nested is empty, it shouldn't be in the YAML
            # (or it would be present but empty)

    def test_load_metadata_with_nested(self):
        """Test loading metadata from file with nested projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a metadata file with nested projects
            metadata_content = """# This is a generated file by dfetch. Don't edit this, but edit the manifest.
# For more info see https://dfetch.rtfd.io/en/latest/getting_started.html
dfetch:
  branch: main
  hash: hash123
  last_fetch: 01/01/2026, 12:30:00
  nested:
  - branch: feature
    destination: ext/nested
    hash: nestedhash
    last_fetch: 01/01/2026, 00:00:00
    patch: []
    remote_url: https://example.com/nested.git
    revision: def456
    tag: v1.0
  patch: main.patch
  remote_url: https://example.com/repo.git
  revision: abc123
  tag: ''
"""
            metadata_file = os.path.join(tmpdir, Metadata.FILENAME)
            with open(metadata_file, "w", encoding="utf-8") as f:
                f.write(metadata_content)

            # Load the metadata
            metadata = Metadata.from_file(metadata_file)

            # Verify the nested projects were loaded
            assert len(metadata.nested) == 1
            assert metadata.nested[0]["remote_url"] == "https://example.com/nested.git"
            assert metadata.nested[0]["destination"] == "ext/nested"
            assert metadata.nested[0]["branch"] == "feature"
            assert metadata.nested[0]["revision"] == "def456"


class TestMetadataMultipleNested:
    """Tests for multiple nested projects."""

    def test_metadata_with_multiple_nested(self):
        """Test metadata with multiple nested projects."""
        nested1: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "branch1",
            "tag": "",
            "revision": "rev1",
            "remote_url": "url1",
            "destination": "ext/nested1",
            "hash": "hash1",
            "patch": [],
            "nested": [],
        }

        nested2: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
            "branch": "branch2",
            "tag": "v2.0",
            "revision": "rev2",
            "remote_url": "url2",
            "destination": "ext/nested2",
            "hash": "hash2",
            "patch": ["patch.txt"],
            "nested": [],
        }

        options: Options = {
            "last_fetch": datetime.datetime(2026, 1, 1, 12, 30, 0),
            "branch": "main",
            "tag": "",
            "revision": "abc123",
            "remote_url": "https://example.com/repo.git",
            "destination": "/path/to/dest",
            "hash": "hash123",
            "patch": [],
            "nested": [nested1, nested2],
        }

        metadata = Metadata(options)

        assert len(metadata.nested) == 2
        assert metadata.nested[0]["destination"] == "ext/nested1"
        assert metadata.nested[1]["destination"] == "ext/nested2"
        assert metadata.nested[1]["tag"] == "v2.0"