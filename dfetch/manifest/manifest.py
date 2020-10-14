"""
A manifest file is a ``.yaml`` file describing what external projects are used in this project.
This can be any external repository (git, svn).

A manifest must consist of a ``manifest:`` block with the ``version:`` of the manifest syntax.
In the block two main block are present.

A block ``remotes`` (see :ref:`remotes`) which contains a list of sources of the projects the download and a block
``projects:`` that contains a list of projects to add.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: somemodule
           dst: Tests/Utils/python/mycompany/
"""
import io
import os
from typing import Union, IO, Dict, Any, List

import yaml

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.remote import Remote
from dfetch.util.util import find_file


class Manifest:
    """Manifest describing all the modules information

    This class is created from the manifest file a project has.
    """

    def __init__(self, manifest_text: Union[io.TextIOWrapper, str, IO[str]]) -> None:
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
        """Creates the manifest from a file path

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
        """ Version of the manifest file """
        return self.__version

    @property
    def projects(self) -> List[ProjectEntry]:
        """ Get a list of Projects from the manifest """
        return list(self._projects.values())


def find_manifest() -> str:
    """ Find a manifest """
    paths = find_file("manifest.yaml", ".")

    if len(paths) == 0:
        raise RuntimeError("No manifests were found!")
    if len(paths) != 1:
        raise RuntimeError(f"Multiple manifests found: {paths}")

    return os.path.realpath(paths[0])
