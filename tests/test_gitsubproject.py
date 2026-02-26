"""Test GitSubProject with submodule support."""

# mypy: ignore-errors
# flake8: noqa

import datetime
from unittest.mock import Mock, patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.metadata import Options
from dfetch.vcs.git import Submodule


class TestGitSubProjectFetchWithNested:
    """Tests for GitSubProject._fetch_impl with nested submodules."""

    def test_fetch_impl_returns_nested_submodules(self):
        """Test that _fetch_impl returns nested submodules."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        # Mock submodules returned by checkout_version
        mock_submodules = [
            Submodule(
                name="submodule1",
                toplevel="/tmp/test-dest",
                path="ext/sub1",
                sha="abc123",
                url="https://example.com/sub1.git",
                branch="main",
                tag="",
            ),
            Submodule(
                name="submodule2",
                toplevel="/tmp/test-dest",
                path="ext/sub2",
                sha="def456",
                url="https://example.com/sub2.git",
                branch="",
                tag="v1.0",
            ),
        ]

        mock_local_repo = Mock()
        mock_local_repo.checkout_version.return_value = ("fetched_sha_123", mock_submodules)
        mock_local_repo.METADATA_DIR = ".git"
        mock_local_repo.GIT_MODULES_FILE = ".gitmodules"

        version_to_fetch = Version(branch="main")

        with patch("dfetch.project.gitsubproject.GitLocalRepo", return_value=mock_local_repo):
            with patch("dfetch.project.gitsubproject.pathlib.Path.mkdir"):
                with patch("dfetch.project.gitsubproject.safe_rmtree"):
                    with patch("dfetch.project.gitsubproject.safe_rm"):
                        with patch.object(
                            subproject, "_determine_what_to_fetch", return_value="main"
                        ):
                            with patch.object(
                                subproject,
                                "_determine_fetched_version",
                                return_value=Version(branch="main", revision="fetched_sha_123"),
                            ):
                                fetched_version, nested = subproject._fetch_impl(version_to_fetch)

        # Verify nested submodules were returned
        assert len(nested) == 2

        # Check first submodule
        assert nested[0]["remote_url"] == "https://example.com/sub1.git"
        assert nested[0]["destination"] == "ext/sub1"
        assert nested[0]["branch"] == "main"
        assert nested[0]["tag"] == ""
        assert nested[0]["revision"] == "abc123"
        assert isinstance(nested[0]["last_fetch"], datetime.datetime)

        # Check second submodule
        assert nested[1]["remote_url"] == "https://example.com/sub2.git"
        assert nested[1]["destination"] == "ext/sub2"
        assert nested[1]["branch"] == ""
        assert nested[1]["tag"] == "v1.0"
        assert nested[1]["revision"] == "def456"

    def test_fetch_impl_no_submodules(self):
        """Test _fetch_impl when there are no submodules."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        mock_local_repo = Mock()
        mock_local_repo.checkout_version.return_value = ("fetched_sha_123", [])
        mock_local_repo.METADATA_DIR = ".git"
        mock_local_repo.GIT_MODULES_FILE = ".gitmodules"

        version_to_fetch = Version(branch="main")

        with patch("dfetch.project.gitsubproject.GitLocalRepo", return_value=mock_local_repo):
            with patch("dfetch.project.gitsubproject.pathlib.Path.mkdir"):
                with patch("dfetch.project.gitsubproject.safe_rmtree"):
                    with patch("dfetch.project.gitsubproject.safe_rm"):
                        with patch.object(
                            subproject, "_determine_what_to_fetch", return_value="main"
                        ):
                            with patch.object(
                                subproject,
                                "_determine_fetched_version",
                                return_value=Version(branch="main", revision="fetched_sha_123"),
                            ):
                                fetched_version, nested = subproject._fetch_impl(version_to_fetch)

        # Verify no nested submodules
        assert len(nested) == 0
        assert nested == []

    def test_fetch_impl_nested_options_structure(self):
        """Test that nested Options have correct structure."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        mock_submodules = [
            Submodule(
                name="submodule1",
                toplevel="/tmp/test-dest",
                path="ext/sub1",
                sha="abc123",
                url="https://example.com/sub1.git",
                branch="feature",
                tag="",
            ),
        ]

        mock_local_repo = Mock()
        mock_local_repo.checkout_version.return_value = ("fetched_sha_123", mock_submodules)
        mock_local_repo.METADATA_DIR = ".git"
        mock_local_repo.GIT_MODULES_FILE = ".gitmodules"

        version_to_fetch = Version(branch="main")

        with patch("dfetch.project.gitsubproject.GitLocalRepo", return_value=mock_local_repo):
            with patch("dfetch.project.gitsubproject.pathlib.Path.mkdir"):
                with patch("dfetch.project.gitsubproject.safe_rmtree"):
                    with patch("dfetch.project.gitsubproject.safe_rm"):
                        with patch.object(
                            subproject, "_determine_what_to_fetch", return_value="main"
                        ):
                            with patch.object(
                                subproject,
                                "_determine_fetched_version",
                                return_value=Version(branch="main", revision="fetched_sha_123"),
                            ):
                                fetched_version, nested = subproject._fetch_impl(version_to_fetch)

        # Verify all required fields are present in Options
        required_fields = [
            "remote_url",
            "destination",
            "branch",
            "tag",
            "revision",
            "last_fetch",
            "nested",
            "hash",
            "patch",
        ]

        for field in required_fields:
            assert field in nested[0], f"Field '{field}' missing from nested Options"

        # Verify nested is always empty list (no recursive nesting)
        assert nested[0]["nested"] == []
        assert nested[0]["hash"] == ""
        assert nested[0]["patch"] == []


class TestGitSubProjectDetermineFetchedVersion:
    """Tests for GitSubProject._determine_fetched_version."""

    def test_determine_fetched_version_with_tag(self):
        """Test determining fetched version when tag is provided."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        with patch.object(subproject, "get_default_branch", return_value="master"):
            version = Version(tag="v1.0.0")
            result = subproject._determine_fetched_version(version, "abc123")

            assert result.tag == "v1.0.0"
            assert result.branch == "master"
            assert result.revision == ""

    def test_determine_fetched_version_with_revision(self):
        """Test determining fetched version when revision is provided."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        with patch.object(subproject, "get_default_branch", return_value="master"):
            version = Version(revision="abc123")
            result = subproject._determine_fetched_version(version, "abc123")

            assert result.tag == ""
            assert result.branch == "master"
            assert result.revision == "abc123"

    def test_determine_fetched_version_with_branch_and_fetched_sha(self):
        """Test determining fetched version with branch, using fetched SHA."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        version = Version(branch="develop")
        result = subproject._determine_fetched_version(version, "fetched_sha_789")

        assert result.tag == ""
        assert result.branch == "develop"
        assert result.revision == "fetched_sha_789"


class TestGitSubProjectDetermineWhatToFetch:
    """Tests for GitSubProject._determine_what_to_fetch."""

    def test_determine_what_to_fetch_with_revision(self):
        """Test determining what to fetch when revision is provided."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        version = Version(revision="abc123def456789012345678901234567890abcd")
        result = subproject._determine_what_to_fetch(version)

        assert result == "abc123def456789012345678901234567890abcd"

    def test_determine_what_to_fetch_with_tag(self):
        """Test determining what to fetch when tag is provided."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        version = Version(tag="v1.0.0")
        result = subproject._determine_what_to_fetch(version)

        assert result == "v1.0.0"

    def test_determine_what_to_fetch_with_branch(self):
        """Test determining what to fetch when branch is provided."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        version = Version(branch="feature")
        result = subproject._determine_what_to_fetch(version)

        assert result == "feature"

    def test_determine_what_to_fetch_default_branch(self):
        """Test determining what to fetch with default branch."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        with patch.object(subproject._remote_repo, "get_default_branch", return_value="main"):
            version = Version()
            result = subproject._determine_what_to_fetch(version)

            assert result == "main"

    def test_determine_what_to_fetch_short_revision_raises(self):
        """Test that shortened revision raises an error."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        version = Version(revision="abc123")  # Short revision

        with pytest.raises(RuntimeError, match="Shortened revisions"):
            subproject._determine_what_to_fetch(version)

    def test_determine_what_to_fetch_revision_priority(self):
        """Test that revision has priority over tag and branch."""
        project_entry = ProjectEntry(
            {
                "name": "test-project",
                "url": "https://example.com/repo.git",
                "dst": "/tmp/test-dest",
            }
        )

        subproject = GitSubProject(project_entry)

        version = Version(
            revision="abc123def456789012345678901234567890abcd",
            tag="v1.0.0",
            branch="feature",
        )
        result = subproject._determine_what_to_fetch(version)

        # Revision should have priority
        assert result == "abc123def456789012345678901234567890abcd"


class TestGitSubProjectRevisionIsEnough:
    """Tests for GitSubProject.revision_is_enough."""

    def test_revision_is_enough_returns_true(self):
        """Test that git revision is enough to uniquely identify."""
        assert GitSubProject.revision_is_enough() is True