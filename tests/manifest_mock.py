"""Mock for Manifest class."""


from unittest.mock import MagicMock, Mock

from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry


def mock_manifest(projects):
    """Create a manifest mock."""

    project_mocks = []

    for project in projects:
        mock_project = Mock(spec=ProjectEntry)
        mock_project.name = project["name"]
        mock_project.destination = "some_dest"
        project_mocks += [mock_project]

    mocked_manifest = MagicMock(spec=Manifest, projects=project_mocks)
    mocked_manifest.selected_projects.return_value = project_mocks
    return mocked_manifest
