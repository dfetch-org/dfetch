"""All Project related items."""

import dfetch.manifest.project
from dfetch.project.git import GitSubProject
from dfetch.project.subproject import SubProject
from dfetch.project.svn import SvnSubProject

SUPPORTED_PROJECT_TYPES = [GitSubProject, SvnSubProject]


def make(project_entry: dfetch.manifest.project.ProjectEntry) -> SubProject:
    """Create a new SubProject based on a project from the manifest."""
    for project_type in SUPPORTED_PROJECT_TYPES:
        if project_type.NAME == project_entry.vcs:
            return project_type(project_entry)

    for project_type in SUPPORTED_PROJECT_TYPES:
        project = project_type(project_entry)

        if project.check():
            return project
    raise RuntimeError("vcs type unsupported")
