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

import difflib
import io
import os
import pathlib
from typing import IO, Any, Dict, List, Optional, Sequence, Tuple, Union

import yaml
from typing_extensions import TypedDict

from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote, RemoteDict
from dfetch.manifest.validate import validate
from dfetch.util.util import find_file, prefix_runtime_exceptions

logger = get_logger(__name__)


class RequestedProjectNotFoundError(RuntimeError):
    """Exception if items are not found in list of possibilities."""

    def __init__(self, unfound: Sequence[str], possibles: Sequence[str]) -> None:
        """Create an exception."""
        self._possibles = possibles
        quoted_unfound = ", ".join(f'"{name}"' for name in unfound)
        quoted_project_names = ", ".join([f'"{name}"' for name in possibles])
        super().__init__(
            f"Not all projects found! {quoted_unfound}",
            f"This manifest contains: {quoted_project_names}",
            self._make_suggestion(unfound),
        )

    def _make_suggestion(self, unfound: Sequence[str]) -> str:
        """Suggest similar projects."""
        best_guesses = self._guess_project(unfound)

        if best_guesses:
            best_guesses_quoted = (f'"{name}"' for name in best_guesses)
            return f"Did you mean: {' and '.join(best_guesses_quoted)}?"
        return ""

    def _guess_project(self, names: Sequence[str]) -> Sequence[str]:
        """Try guessing a better alternative."""
        if " ".join(names) in self._possibles:
            return [" ".join(names)]

        return [
            guess
            for guess in sorted(
                {
                    (
                        difflib.get_close_matches(
                            name,
                            possibilities=self._possibles,
                            n=1,
                        )
                        or [""]
                    )[0]
                    for name in names
                }
            )
            if guess
        ]


class ManifestDict(  # pylint: disable=too-many-ancestors
    TypedDict, total=False
):  # When https://www.python.org/dev/peps/pep-0655/ is accepted, only make remotes optional
    """Serialized dict types."""

    version: Union[int, str]
    remotes: Sequence[Union[RemoteDict, Remote]]
    projects: Sequence[Union[ProjectEntryDict, ProjectEntry, Dict[str, str]]]


class Manifest:
    """Manifest describing all the modules information.

    This class is created from the manifest file a project has.
    """

    CURRENT_VERSION = "0.0"

    def __init__(self, manifest: ManifestDict) -> None:
        """Create the manifest."""
        self.__version: str = str(manifest.get("version", self.CURRENT_VERSION))

        self._remotes, default_remotes = self._determine_remotes(
            manifest.get("remotes", [])
        )

        if not default_remotes:
            default_remotes = list(self._remotes.values())[0:1]

        self._default_remote_name = (
            "" if not default_remotes else default_remotes[0].name
        )

        if "projects" not in manifest:
            raise KeyError("No projects in manifest!")
        self._projects = self._init_projects(manifest["projects"])

    def _init_projects(
        self, projects: Sequence[Union[ProjectEntryDict, ProjectEntry, Dict[str, str]]]
    ) -> Dict[str, ProjectEntry]:
        """Iterate over projects from manifest and initialize ProjectEntries from it.

        Args:
            projects (Sequence[Union[ProjectEntryDict, ProjectEntry, Dict[str, str]]]): Iterable with projects

        Raises:
            RuntimeError: Project unknown

        Returns:
            Dict[str, ProjectEntry]: Dictionary with key: Name of project, Value: ProjectEntry
        """
        _projects: Dict[str, ProjectEntry] = {}

        for project in projects:
            if isinstance(project, dict):
                if "name" not in project:
                    raise KeyError("Missing name!")
                last_project = _projects[project["name"]] = ProjectEntry.from_yaml(
                    project, self._default_remote_name
                )
            elif isinstance(project, ProjectEntry):
                last_project = _projects[project.name] = ProjectEntry.copy(project)
            else:
                raise RuntimeError(f"{project} has unknown type")

            if last_project.remote:
                try:
                    last_project.set_remote(self._remotes[last_project.remote])
                except KeyError as exc:
                    raise RuntimeError(
                        f"Remote {last_project.remote} of {last_project.name} wasn't found "
                        f"in {list(self._remotes.keys())}!",
                    ) from exc

        return _projects

    @staticmethod
    def _determine_remotes(
        remotes_from_manifest: Sequence[Union[RemoteDict, Remote]],
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
            return ""

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
        with open(path, "r", encoding="utf-8") as opened_file:
            return Manifest.from_yaml(opened_file)

    @property
    def version(self) -> str:
        """Version of the manifest file."""
        return self.__version

    @property
    def projects(self) -> Sequence[ProjectEntry]:
        """Get a list of Projects from the manifest."""
        return list(self._projects.values())

    def selected_projects(self, names: Sequence[str]) -> Sequence[ProjectEntry]:
        """Get a list of Projects from the manifest with the given names."""
        projects = (
            list(
                project for project in self._projects.values() if project.name in names
            )
            if names
            else list(self._projects.values())
        )
        if names and len(projects) != len(names):
            found = [project.name for project in projects]
            unfound = [name for name in names if name not in found]
            possibles = [project.name for project in self._projects.values()]
            raise RequestedProjectNotFoundError(unfound, possibles)
        return projects

    @property
    def remotes(self) -> Sequence[Remote]:
        """Get a list of Remotes from the manifest."""
        return list(self._remotes.values())

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

        if remotes:
            return {
                "manifest": {
                    "version": self.version,
                    "remotes": remotes,
                    "projects": projects,
                }
            }

        return {
            "manifest": {
                "version": self.version,
                "projects": projects,
            }
        }

    def dump(self, path: str) -> None:
        """Dump metadata file to correct path."""
        with open(path, "w+", encoding="utf-8") as manifest_file:
            yaml.dump(
                self._as_dict(), manifest_file, Dumper=ManifestDumper, sort_keys=False
            )


def find_manifest() -> str:
    """Find a manifest."""
    paths = find_file(DEFAULT_MANIFEST_NAME, ".")

    if len(paths) == 0:
        raise RuntimeError("No manifests were found!")
    if len(paths) != 1:
        logger.warning(
            f"Multiple manifests found, using {pathlib.Path(paths[0]).as_posix()}"
        )

    return os.path.realpath(paths[0])


def get_manifest() -> Tuple[Manifest, str]:
    """Get manifest and its path."""
    logger.debug("Looking for manifest")
    manifest_path = find_manifest()
    validate(manifest_path)

    logger.debug(f"Using manifest {manifest_path}")
    return (
        Manifest.from_file(manifest_path),
        manifest_path,
    )


def get_childmanifests(skip: Optional[List[str]] = None) -> List[Tuple[Manifest, str]]:
    """Get manifest and its path."""
    skip = skip or []
    logger.debug("Looking for sub-manifests")

    childmanifests: List[Tuple[Manifest, str]] = []
    for path in find_file(DEFAULT_MANIFEST_NAME, "."):
        path = os.path.realpath(path)
        if path not in skip:
            logger.debug(f"Found sub-manifests {path}")
            with prefix_runtime_exceptions(
                pathlib.Path(path).relative_to(os.path.dirname(os.getcwd())).as_posix()
            ):
                validate(path)
            childmanifest = Manifest.from_file(path)
            childmanifests += [(childmanifest, path)]

    return childmanifests


class ManifestDumper(yaml.SafeDumper):  # pylint: disable=too-many-ancestors
    """Dump a manifest YAML.

    HACK: insert blank lines between top-level objects
    inspired by https://stackoverflow.com/a/44284819/3786245
    """

    _last_additional_break = 0

    def write_line_break(self, data: Any = None) -> None:
        """Write a line break."""
        super().write_line_break(data)  # type: ignore[unused-ignore]

        if len(self.indents) == 2 and getattr(self.event, "value", "") != "version":
            super().write_line_break()  # type: ignore[unused-ignore]

        if len(self.indents) == 3 and self._last_additional_break != 2:
            super().write_line_break()  # type: ignore[unused-ignore]

        self._last_additional_break = len(self.indents)
