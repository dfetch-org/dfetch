"""All Project related items."""
import logging

import dfetch.manifest.project
from dfetch.project.git import GitRepo
from dfetch.project.svn import SvnRepo
from dfetch.project.vcs import VCS

SUPPORTED_PROJECT_TYPES = [GitRepo, SvnRepo]


def make(
    project_entry: dfetch.manifest.project.ProjectEntry, logger: logging.Logger
) -> VCS:
    """Create a new VCS based on a project from the manifest."""
    for project_type in SUPPORTED_PROJECT_TYPES:
        project = project_type(project_entry, logger)

        if project.check():
            return project
    raise RuntimeError("vcs type unsupported")
