"""Super project abstraction.

This module provides the SuperProject class which represents the project that
contains the `dfetch.yaml` manifest file (the "super project"). It provides
helpers to query VCS information about that repository (for example whether
it's a git or svn repository).
"""

from __future__ import annotations

import os

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest, find_manifest
from dfetch.manifest.validate import validate

logger = get_logger(__name__)


class SuperProject:
    """Representation of the project containing the manifest.

    A SuperProject is the repository/directory that contains the dfetch
    manifest file. It exposes helpers to determine whether that project is
    managed by git, svn, or is unversioned.
    """

    def __init__(self) -> None:
        """Create a SuperProject by looking for a manifest file."""
        logger.debug("Looking for manifest")
        manifest_path = find_manifest()
        validate(manifest_path)

        logger.debug(f"Using manifest {manifest_path}")
        self._manifest = Manifest.from_file(manifest_path)
        self._root_directory = os.path.dirname(self._manifest.path)

    @property
    def root_directory(self) -> str:
        """Return the directory that contains the manifest file."""
        return self._root_directory

    @property
    def manifest(self) -> Manifest:
        """The manifest of the super project."""
        return self._manifest
