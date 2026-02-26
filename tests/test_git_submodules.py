"""Test git submodule functionality."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import Mock, patch

import pytest

from dfetch.vcs.git import GitLocalRepo, GitRemote, Submodule


class TestSubmodule:
    """Tests for Submodule NamedTuple."""

    def test_submodule_creation(self):
        """Test creating a Submodule."""
        submodule = Submodule(
            name="test-submodule",
            toplevel="/path/to/toplevel",
            path="ext/submodule",
            sha="abc123def456",
            url="https://example.com/submodule.git",
            branch="main",
            tag="v1.0",
        )

        assert submodule.name == "test-submodule"
        assert submodule.toplevel == "/path/to/toplevel"
        assert submodule.path == "ext/submodule"
        assert submodule.sha == "abc123def456"
        assert submodule.url == "https://example.com/submodule.git"
        assert submodule.branch == "main"
        assert submodule.tag == "v1.0"

    def test_submodule_as_tuple(self):
        """Test that Submodule can be used as a tuple."""
        submodule = Submodule("name", "top", "path", "sha", "url", "branch", "tag")

        # Test unpacking
        name, toplevel, path, sha, url, branch, tag = submodule

        assert name == "name"
        assert toplevel == "top"
        assert path == "path"
        assert sha == "sha"
        assert url == "url"
        assert branch == "branch"
        assert tag == "tag"


class TestGitRemoteBranchOrTagFromSha:
    """Tests for GitRemote.find_branch_tip_or_tag_from_sha."""

    @pytest.mark.parametrize(
        "name, sha, expected_branch, expected_tag",
        [
            ("branch-tip", "abc123", "main", ""),
            ("tag", "def456", "", "v1.0"),
            ("neither", "xyz789", "", ""),
            ("short-sha", "abc", "main", ""),  # "abc" matches "abc123" first (startswith)
        ],
    )
    def test_find_branch_tip_or_tag_from_sha(
        self, name, sha, expected_branch, expected_tag
    ):
        """Test finding branch or tag from SHA."""
        # Mock ls_remote to return test data
        mock_info = {
            "refs/heads/main": "abc123",
            "refs/heads/feature": "abc12345",  # Starts with "abc"
            "refs/tags/v1.0": "def456",
            "refs/tags/v2.0": "ghi789",
        }

        remote = GitRemote("https://example.com/repo.git")

        with patch.object(remote, "_ls_remote", return_value=mock_info):
            branch, tag = remote.find_branch_tip_or_tag_from_sha(sha)

            assert branch == expected_branch
            assert tag == expected_tag


class TestGitLocalRepoSubmodules:
    """Tests for GitLocalRepo.submodules()."""

    def test_submodules_parsing(self):
        """Test parsing submodule output."""
        # Mock the git submodule foreach output
        mock_output = """submodule1 ext/sub1 abc123 /path/to/toplevel
submodule2 ext/sub2 def456 /path/to/toplevel
"""
        mock_result = Mock()
        mock_result.stdout.decode.return_value = mock_output

        # Mock submodule URLs
        mock_urls = {
            "submodule1": "https://example.com/sub1.git",
            "submodule2": "https://example.com/sub2.git",
        }

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            with patch.object(
                GitLocalRepo, "_get_submodule_urls", return_value=mock_urls
            ):
                with patch.object(
                    GitRemote, "find_branch_tip_or_tag_from_sha", return_value=("main", "")
                ):
                    submodules = GitLocalRepo.submodules()

                    assert len(submodules) == 2
                    assert submodules[0].name == "submodule1"
                    assert submodules[0].path == "ext/sub1"
                    assert submodules[0].sha == "abc123"
                    assert submodules[0].url == "https://example.com/sub1.git"
                    assert submodules[0].branch == "main"

                    assert submodules[1].name == "submodule2"
                    assert submodules[1].path == "ext/sub2"

    def test_submodules_empty(self):
        """Test when there are no submodules."""
        mock_result = Mock()
        mock_result.stdout.decode.return_value = ""

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            submodules = GitLocalRepo.submodules()

            assert len(submodules) == 0

    def test_submodules_with_tag(self):
        """Test submodules that point to tags."""
        mock_output = "submodule1 ext/sub1 abc123 /path/to/toplevel\n"
        mock_result = Mock()
        mock_result.stdout.decode.return_value = mock_output

        mock_urls = {"submodule1": "https://example.com/sub1.git"}

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            with patch.object(
                GitLocalRepo, "_get_submodule_urls", return_value=mock_urls
            ):
                with patch.object(
                    GitRemote, "find_branch_tip_or_tag_from_sha", return_value=("", "v1.0")
                ):
                    submodules = GitLocalRepo.submodules()

                    assert len(submodules) == 1
                    assert submodules[0].tag == "v1.0"
                    assert submodules[0].branch == ""

    def test_submodules_fallback_to_local_branch(self):
        """Test finding branch from local repo when remote doesn't have it."""
        mock_output = "submodule1 ext/sub1 abc123 /path/to/toplevel\n"
        mock_result = Mock()
        mock_result.stdout.decode.return_value = mock_output

        mock_urls = {"submodule1": "https://example.com/sub1.git"}

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            with patch.object(
                GitLocalRepo, "_get_submodule_urls", return_value=mock_urls
            ):
                with patch.object(
                    GitRemote, "find_branch_tip_or_tag_from_sha", return_value=("", "")
                ):
                    with patch.object(
                        GitLocalRepo,
                        "find_branch_containing_sha",
                        return_value="local-branch",
                    ):
                        submodules = GitLocalRepo.submodules()

                        assert len(submodules) == 1
                        assert submodules[0].branch == "local-branch"
                        assert submodules[0].tag == ""


class TestGitLocalRepoGetSubmoduleUrls:
    """Tests for GitLocalRepo._get_submodule_urls()."""

    def test_get_submodule_urls(self):
        """Test parsing submodule URLs from git config."""
        mock_output = """submodule.sub1.url https://example.com/sub1.git
submodule.sub2.url https://example.com/sub2.git
"""
        mock_result = Mock()
        mock_result.stdout.decode.return_value = mock_output

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            with patch.object(GitLocalRepo, "get_remote_url", return_value=""):
                urls = GitLocalRepo._get_submodule_urls("/path/to/toplevel")

                assert urls == {
                    "sub1": "https://example.com/sub1.git",
                    "sub2": "https://example.com/sub2.git",
                }

    def test_get_submodule_urls_relative(self):
        """Test resolving relative submodule URLs."""
        mock_output = """submodule.sub1.url ../relative/sub1.git
submodule.sub2.url ../../another/sub2.git
"""
        mock_result = Mock()
        mock_result.stdout.decode.return_value = mock_output

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            with patch.object(
                GitLocalRepo,
                "get_remote_url",
                return_value="https://example.com/org/repo.git",
            ):
                urls = GitLocalRepo._get_submodule_urls("/path/to/toplevel")

                assert urls["sub1"] == "https://example.com/org/relative/sub1.git"
                assert urls["sub2"] == "https://example.com/another/sub2.git"


class TestGitLocalRepoEnsureAbsUrl:
    """Tests for GitLocalRepo._ensure_abs_url()."""

    @pytest.mark.parametrize(
        "name, root_url, rel_url, expected",
        [
            (
                "absolute",
                "https://example.com/org/repo.git",
                "https://other.com/sub.git",
                "https://other.com/sub.git",
            ),
            (
                "relative-one-level",
                "https://example.com/org/repo.git",
                "../sibling.git",
                "https://example.com/org/sibling.git",
            ),
            (
                "relative-two-levels",
                "https://example.com/org/team/repo.git",
                "../../other/sub.git",
                "https://example.com/org/other/sub.git",
            ),
            (
                "relative-complex",
                "https://example.com/a/b/c/d.git",
                "../../../x/y.git",
                "https://example.com/a/x/y.git",
            ),
        ],
    )
    def test_ensure_abs_url(self, name, root_url, rel_url, expected):
        """Test ensuring absolute URLs."""
        result = GitLocalRepo._ensure_abs_url(root_url, rel_url)
        assert result == expected


class TestGitLocalRepoFindBranchContainingSha:
    """Tests for GitLocalRepo.find_branch_containing_sha()."""

    def test_find_branch_containing_sha(self):
        """Test finding branch that contains a SHA."""
        mock_output = "  feature-branch\n* main\n  another-branch\n"
        mock_result = Mock()
        mock_result.stdout.decode.return_value = mock_output

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            with patch("dfetch.vcs.git.in_directory"):
                with patch("os.path.isdir", return_value=True):
                    repo = GitLocalRepo("/path/to/repo")
                    branch = repo.find_branch_containing_sha("abc123")

                    # Should return first branch (after splitting by *)
                    assert branch == "feature-branch"

    def test_find_branch_no_branches(self):
        """Test when no branches contain the SHA."""
        mock_output = ""
        mock_result = Mock()
        mock_result.stdout.decode.return_value = mock_output

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            with patch("dfetch.vcs.git.in_directory"):
                with patch("os.path.isdir", return_value=True):
                    repo = GitLocalRepo("/path/to/repo")
                    branch = repo.find_branch_containing_sha("abc123")

                    assert branch == ""

    def test_find_branch_detached_head(self):
        """Test handling detached HEAD state."""
        # When in detached HEAD, split by "*" yields empty string & detached HEAD msg
        # The implementation filters out "HEAD detached" messages, leaving nothing
        mock_output = "* (HEAD detached at abc123)\n  main\n"
        mock_result = Mock()
        mock_result.stdout.decode.return_value = mock_output

        with patch("dfetch.vcs.git.run_on_cmdline", return_value=mock_result):
            with patch("dfetch.vcs.git.in_directory"):
                with patch("os.path.isdir", return_value=True):
                    repo = GitLocalRepo("/path/to/repo")
                    branch = repo.find_branch_containing_sha("abc123")

                    # Returns empty string when only detached HEAD is present
                    assert branch == ""

    def test_find_branch_no_git_dir(self):
        """Test when .git directory doesn't exist."""
        with patch("os.path.isdir", return_value=False):
            repo = GitLocalRepo("/path/to/repo")
            branch = repo.find_branch_containing_sha("abc123")

            assert branch == ""