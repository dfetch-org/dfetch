"""A manifest file is a ``.yaml`` file describing what external projects are used in this project.

This can be any external repository (git, svn).
A manifest must consist of a ``manifest:`` section with the ``version:`` of the manifest syntax.
In the section two subsections are present.

A section ``remotes`` (see :ref:`remotes`) which contains a list of sources of the projects to
download and a section ``projects:`` that contains a list of projects to fetch.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule
           dst: external/mymodule/
"""
import io
import logging
import os
from typing import IO, Any, Dict, List, Tuple, Union

import yaml

import dfetch.manifest.validate
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.remote import Remote
from dfetch.util.util import find_file

logger = logging.getLogger(__name__)


class Manifest:
    """Manifest describing all the modules information.

    This class is created from the manifest file a project has.
    """

    def __init__(self, manifest_text: Union[io.TextIOWrapper, str, IO[str]]) -> None:
        """Create the manifest."""
        loaded_yaml = self._load_yaml(manifest_text)

        if not loaded_yaml:
            raise RuntimeError("Manifest is not valid YAML")

        manifest = loaded_yaml["manifest"]

        if not manifest:
            raise RuntimeError("Missing manifest root element!")

        self.__version: str = manifest["version"]

        self._remotes = {
            remote["name"]: Remote(remote) for remote in manifest["remotes"]
        }

        default_remotes = [
            remote for remote in self._remotes.values() if remote.is_default
        ] or list(self._remotes.values())[0:1]

        self._projects: Dict[str, ProjectEntry] = {
            project["name"]: ProjectEntry(project, default_remotes[0])
            for project in manifest["projects"]
        }

        for project in self._projects.values():
            if project.remote:
                project.set_remote(self._remotes[project.remote])

    @staticmethod
    def _load_yaml(text: Union[io.TextIOWrapper, str, IO[str]]) -> Any:
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            print(exc)

    @staticmethod
    def from_file(path: str) -> "Manifest":
        """Create a manifest from a file path.

        Args:
            path:
                Path to a manifest file.

        Returns:
             A Manifest object that can be used directly.

        Raises:
            FileNotFoundError: Given path was not a file.
        """
        with open(path, "r") as opened_file:
            return Manifest(opened_file)

    @property
    def version(self) -> str:
        """Version of the manifest file."""
        return self.__version

    @property
    def projects(self) -> List[ProjectEntry]:
        """Get a list of Projects from the manifest."""
        return list(self._projects.values())


def find_manifest() -> str:
    """Find a manifest."""
    paths = find_file("manifest.yaml", ".")

    if len(paths) == 0:
        raise RuntimeError("No manifests were found!")
    if len(paths) != 1:
        raise RuntimeError(f"Multiple manifests found: {paths}")

    return os.path.realpath(paths[0])


def get_manifest() -> Tuple[Manifest, str]:
    """Get manifest and its path."""
    logger.debug("Looking for manifest")
    manifest_path = find_manifest()
    dfetch.manifest.validate.validate(manifest_path)

    logger.debug(f"Using manifest {manifest_path}")
    return (
        dfetch.manifest.manifest.Manifest.from_file(manifest_path),
        manifest_path,
    )
