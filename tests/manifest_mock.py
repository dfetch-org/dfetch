"""Mock for Manifest class."""

from unittest.mock import MagicMock, Mock

from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry


def mock_manifest(projects, path: str = "/some/path") -> MagicMock:
    """Create a manifest mock."""

    project_mocks = []

    for project in projects:
        mock_project = Mock(spec=ProjectEntry)
        mock_project.name = project["name"]
        mock_project.destination = "some_dest"
        mock_project.remote = ""
        project_mocks += [mock_project]

    mocked_manifest = MagicMock(spec=Manifest, projects=project_mocks, path=path)
    mocked_manifest.selected_projects.return_value = project_mocks

    mocked_manifest.check_name_uniqueness.side_effect = lambda name: (
        Manifest.check_name_uniqueness(mocked_manifest, name)
    )
    mocked_manifest.guess_destination.side_effect = lambda name: (
        Manifest.guess_destination(mocked_manifest, name)
    )
    mocked_manifest.find_remote_for_url.side_effect = lambda url: (
        Manifest.find_remote_for_url(mocked_manifest, url)
    )

    return mocked_manifest
