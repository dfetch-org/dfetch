"""A manifest file is a ``.yaml`` file describing what external projects are used in this project.

This can be any external repository (git, svn).
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
import os
from typing import IO, Any, Dict, List, Sequence, Tuple, Union

import yaml
from typing_extensions import TypedDict

import dfetch.manifest.validate
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote, RemoteDict
from dfetch.util.util import find_file

logger = get_logger(__name__)


class ManifestDict(TypedDict):
    """Serialized dict types."""

    version: str
    remotes: Sequence[Union[RemoteDict, Remote]]
    projects: Sequence[Union[ProjectEntryDict, ProjectEntry, Dict[str, str]]]


class Manifest:
    """Manifest describing all the modules information.

    This class is created from the manifest file a project has.
    """

    CURRENT_VERSION = "0.0"

    def __init__(self, manifest: ManifestDict) -> None:
        """Create the manifest."""
        self.__version: str = manifest.get("version", self.CURRENT_VERSION)

        self._remotes, default_remotes = self._determine_remotes(manifest["remotes"])

        if not default_remotes:
            default_remotes = list(self._remotes.values())[0:1]

        self._projects: Dict[str, ProjectEntry] = {}
        for project in manifest["projects"]:
            if isinstance(project, dict):
                last_project = self._projects[project["name"]] = ProjectEntry.from_yaml(
                    project, default_remotes[0]
                )
            elif isinstance(project, ProjectEntry):
                last_project = self._projects[project.name] = ProjectEntry.copy(
                    project, default_remotes[0]
                )
            else:
                raise RuntimeError(f"{project} has unknown type")

            if last_project.remote:
                last_project.set_remote(self._remotes[last_project.remote])

    @staticmethod
    def _determine_remotes(
        remotes_from_manifest: Sequence[Union[RemoteDict, Remote]]
    ) -> Tuple[Dict[str, Remote], List[Remote]]:
        default_remotes: List[Remote] = []
        remotes: Dict[str, Remote] = {}
        for remote in remotes_from_manifest:
            if isinstance(remote, dict):
                last_remote = remotes[remote["name"]] = Remote.from_yaml(remote)
            elif isinstance(remote, Remote):
                last_remote = remotes[remote.name] = Remote.copy(remote)
            else:
                raise RuntimeError(f"{remote} has unknown type")

            if last_remote.is_default:
                default_remotes.append(last_remote)

        return (remotes, default_remotes)

    @staticmethod
    def from_yaml(text: Union[io.TextIOWrapper, str, IO[str]]) -> "Manifest":
        """Create a manifest from a file like object."""
        loaded_yaml = Manifest._load_yaml(text)

        if not loaded_yaml:
            raise RuntimeError("Manifest is not valid YAML")

        manifest = loaded_yaml["manifest"]

        if not manifest:
            raise RuntimeError("Missing manifest root element!")

        return Manifest(manifest)

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
            return Manifest.from_yaml(opened_file)

    @property
    def version(self) -> str:
        """Version of the manifest file."""
        return self.__version

    @property
    def projects(self) -> Sequence[ProjectEntry]:
        """Get a list of Projects from the manifest."""
        return list(self._projects.values())

    def __repr__(self) -> str:
        """Get string representing this object."""
        return str(self._as_dict())

    def _as_dict(self) -> Dict[str, ManifestDict]:
        """Get this manifest as dict."""
        remotes: Sequence[RemoteDict] = [
            remote.as_yaml() for remote in self._remotes.values()
        ]

        if len(remotes) == 1:
            remotes[0].pop("default", None)

        projects: List[Dict[str, str]] = []
        for project in self.projects:
            project_yaml: Dict[str, str] = project.as_yaml()
            if len(remotes) == 1:
                project_yaml.pop("remote", None)
            projects.append(project_yaml)

        return {
            "manifest": {
                "version": self.version,
                "remotes": remotes,
                "projects": projects,
            }
        }

    def dump(self, path: str) -> None:
        """Dump metadata file to correct path."""
        with open(path, "w+") as manifest_file:
            yaml.dump(
                self._as_dict(), manifest_file, Dumper=ManifestDumper, sort_keys=False
            )


def find_manifest() -> str:
    """Find a manifest."""
    paths = find_file(DEFAULT_MANIFEST_NAME, ".")

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


class ManifestDumper(yaml.SafeDumper):  # pylint: disable=too-many-ancestors
    """Dump a manifest YAML.

    HACK: insert blank lines between top-level objects
    inspired by https://stackoverflow.com/a/44284819/3786245
    """

    def write_line_break(self, data: Any = None) -> None:
        """Write a line break."""
        super().write_line_break(data)  # type: ignore

        if len(self.indents) == 3:
            super().write_line_break()  # type: ignore
