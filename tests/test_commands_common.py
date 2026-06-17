"""Tests for dfetch/commands/common.py."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import MagicMock, Mock, call, patch

import pytest

from dfetch.commands.common import _make_recommendation, check_sub_manifests
from dfetch.manifest.project import ProjectEntry


def _make_project_mock(remote_url: str) -> Mock:
    """Return a Mock that quacks like a ProjectEntry."""
    project = Mock(spec=ProjectEntry)
    project.remote_url = remote_url
    project.as_recommendation.return_value = project
    project.as_yaml.return_value = {"name": "proj", "url": remote_url}
    return project


def _make_manifest_mock(path: str, project_urls: list) -> Mock:
    """Return a mock that looks like a Manifest."""
    manifest = Mock()
    manifest.path = path
    manifest.projects = [_make_project_mock(url) for url in project_urls]
    return manifest


def _make_submanifest_mock(path: str, project_urls: list) -> Mock:
    """Return a mock submanifest with projects."""
    submanifest = Mock()
    submanifest.path = path
    submanifest.projects = [_make_project_mock(url) for url in project_urls]
    return submanifest


def test_check_sub_manifests_no_submanifests():
    """When get_submanifests returns an empty list, no warning is logged."""
    manifest = _make_manifest_mock(
        "/parent/dfetch.yaml", ["http://example.com/repo.git"]
    )
    parent_project = Mock(spec=ProjectEntry)
    parent_project.name = "parent"

    with patch("dfetch.commands.common.get_submanifests", return_value=[]) as mock_get:
        with patch("dfetch.commands.common.logger") as mock_logger:
            check_sub_manifests(manifest, parent_project)

            mock_logger.print_warning_line.assert_not_called()


def test_check_sub_manifests_all_already_present():
    """When submanifest projects are all in the parent manifest, no warning is logged."""
    url = "http://example.com/repo.git"
    manifest = _make_manifest_mock("/parent/dfetch.yaml", [url])
    parent_project = Mock(spec=ProjectEntry)
    parent_project.name = "parent"

    submanifest = _make_submanifest_mock("/parent/sub/dfetch.yaml", [url])

    with patch("dfetch.commands.common.get_submanifests", return_value=[submanifest]):
        with patch("dfetch.commands.common.logger") as mock_logger:
            check_sub_manifests(manifest, parent_project)

            mock_logger.print_warning_line.assert_not_called()


def test_check_sub_manifests_new_project_warns():
    """When a submanifest project URL is not in the parent manifest, a warning is logged."""
    parent_url = "http://example.com/parent.git"
    sub_url = "http://example.com/new_dep.git"

    manifest = _make_manifest_mock("/parent/dfetch.yaml", [parent_url])
    parent_project = Mock(spec=ProjectEntry)
    parent_project.name = "parent"

    submanifest = _make_submanifest_mock("/parent/sub/dfetch.yaml", [sub_url])

    with patch("dfetch.commands.common.get_submanifests", return_value=[submanifest]):
        with patch("dfetch.commands.common.logger") as mock_logger:
            with patch("os.path.relpath", return_value="sub/dfetch.yaml"):
                check_sub_manifests(manifest, parent_project)

                mock_logger.print_warning_line.assert_called_once()


def test_check_sub_manifests_skips_own_manifest():
    """get_submanifests must be called with skip=[manifest.path]."""
    manifest = _make_manifest_mock("/parent/dfetch.yaml", [])
    parent_project = Mock(spec=ProjectEntry)
    parent_project.name = "parent"

    with patch("dfetch.commands.common.get_submanifests", return_value=[]) as mock_get:
        check_sub_manifests(manifest, parent_project)

        mock_get.assert_called_once_with(skip=["/parent/dfetch.yaml"])


def test_make_recommendation_logs_warning():
    """_make_recommendation logs a warning that mentions the project name and submanifest path."""
    project = Mock(spec=ProjectEntry)
    project.name = "my_project"

    recommendation = Mock(spec=ProjectEntry)
    recommendation.as_yaml.return_value = {
        "name": "dep",
        "url": "http://example.com/dep.git",
    }

    with patch("dfetch.commands.common.logger") as mock_logger:
        _make_recommendation(project, [recommendation], "sub/dfetch.yaml")

        mock_logger.print_warning_line.assert_called_once()
        args = mock_logger.print_warning_line.call_args[0]
        assert args[0] == "my_project"
        assert "sub/dfetch.yaml" in args[1]
