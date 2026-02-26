"""Test StdoutReporter with nested projects support."""

# mypy: ignore-errors
# flake8: noqa

import datetime
import tempfile
from unittest.mock import Mock

from dfetch.manifest.project import ProjectEntry
from dfetch.project.metadata import Metadata, Options
from dfetch.reporting.stdout_reporter import StdoutReporter


class TestStdoutReporterName:
    """Tests for StdoutReporter.name."""

    def test_reporter_name(self):
        """Test that reporter has correct name."""
        mock_manifest = Mock()
        reporter = StdoutReporter(mock_manifest)
        assert reporter.name == "stdout"


class TestStdoutReporterDumpToFile:
    """Tests for StdoutReporter.dump_to_file."""

    def test_dump_to_file_returns_false(self):
        """Test that dump_to_file returns False (no-op for stdout reporter)."""
        mock_manifest = Mock()
        reporter = StdoutReporter(mock_manifest)
        result = reporter.dump_to_file("dummy.txt")

        assert result is False


class TestMetadataWithNestedIntegration:
    """Integration tests for metadata with nested projects."""

    def test_metadata_dumps_nested_correctly(self):
        """Test that metadata with nested projects is dumped correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested options
            nested_options: Options = {
                "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
                "branch": "feature",
                "tag": "v1.0",
                "revision": "def456",
                "remote_url": "https://example.com/nested.git",
                "destination": "ext/nested",
                "hash": "nestedhash",
                "patch": [],
                "nested": [],
            }

            # Create main metadata with nested
            main_options: Options = {
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

            metadata = Metadata(main_options)
            metadata.dump()

            # Verify the nested data is present
            loaded_metadata = Metadata.from_file(metadata.path)
            assert len(loaded_metadata.nested) == 1
            assert loaded_metadata.nested[0]["remote_url"] == "https://example.com/nested.git"

    def test_metadata_with_multiple_nested_projects(self):
        """Test metadata with multiple nested projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested1: Options = {
                "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
                "branch": "branch1",
                "tag": "",
                "revision": "rev1",
                "remote_url": "https://example.com/nested1.git",
                "destination": "ext/nested1",
                "hash": "hash1",
                "patch": [],
                "nested": [],
            }

            nested2: Options = {
                "last_fetch": datetime.datetime(2026, 1, 1, 0, 0, 0),
                "branch": "",
                "tag": "v2.0",
                "revision": "rev2",
                "remote_url": "https://example.com/nested2.git",
                "destination": "ext/nested2",
                "hash": "hash2",
                "patch": ["nested.patch"],
                "nested": [],
            }

            main_options: Options = {
                "last_fetch": datetime.datetime(2026, 1, 1, 12, 30, 0),
                "branch": "main",
                "tag": "",
                "revision": "abc123",
                "remote_url": "https://example.com/repo.git",
                "destination": tmpdir,
                "hash": "hash123",
                "patch": [],
                "nested": [nested1, nested2],
            }

            metadata = Metadata(main_options)
            metadata.dump()

            # Verify both nested projects are present
            loaded_metadata = Metadata.from_file(metadata.path)
            assert len(loaded_metadata.nested) == 2
            assert loaded_metadata.nested[0]["destination"] == "ext/nested1"
            assert loaded_metadata.nested[1]["destination"] == "ext/nested2"