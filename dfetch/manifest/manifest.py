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
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import IO, Any

import yaml
from strictyaml import load
from strictyaml.ruamel.comments import CommentedMap
from strictyaml.ruamel.error import CommentMark
from strictyaml.ruamel.scalarstring import SingleQuotedScalarString
from strictyaml.ruamel.tokens import CommentToken
from typing_extensions import NotRequired, TypedDict

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote, RemoteDict

logger = get_logger(__name__)


def _yaml_str(value: str) -> str | SingleQuotedScalarString:
    """Return SingleQuotedScalarString if value would be misread as non-string."""
    if not isinstance(yaml.safe_load(value), str):
        return SingleQuotedScalarString(value)
    return value


@dataclass
class ManifestEntryLocation:
    """Location of an entry in the manifest file."""

    line_number: int
    start: int
    end: int


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


class ManifestDict(TypedDict, total=True):  # pylint: disable=too-many-ancestors
    """Serialized dict types."""

    version: int | str
    remotes: NotRequired[Sequence[RemoteDict | Remote]]
    projects: Sequence[
        ProjectEntryDict | ProjectEntry | dict[str, str | list[str] | dict[str, str]]
    ]


class Manifest:  # pylint: disable=too-many-instance-attributes
    """Manifest describing all the modules information.

    This class is created from the manifest file a project has.
    """

    CURRENT_VERSION = "0.0"
    _UNSAFE_NAME_RE = re.compile(r"[\x00-\x1F\x7F-\x9F:#\[\]{}&*!|>'\"%@`]")

    _VERSION_KEYS: tuple[str, ...] = ("revision", "tag", "branch")

    def __init__(
        self,
        manifest: ManifestDict,
        text: str | None = None,
        path: str | os.PathLike[str] | None = None,
    ) -> None:
        """Create the manifest."""
        self.__version: str = str(manifest.get("version", self.CURRENT_VERSION))
        self.__text: str = text if text else ""
        self.__path: str = str(path) if path else ""
        self.__relative_path: str = (
            os.path.relpath(self.__path, os.getcwd()) if self.__path else ""
        )
        self._doc = load(self.__text)

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
        self,
        projects: Sequence[
            ProjectEntryDict
            | ProjectEntry
            | dict[str, str | list[str] | dict[str, str]]
        ],
    ) -> dict[str, ProjectEntry]:
        """Iterate over projects from manifest and initialize ProjectEntries from it.

        Args:
            projects (Sequence[
                Union[ProjectEntryDict, ProjectEntry, Dict[str, Union[str, list[str], dict[str, str]]]]
            ]): Iterable with projects

        Raises:
            RuntimeError: Project unknown

        Returns:
            Dict[str, ProjectEntry]: Dictionary with key: Name of project, Value: ProjectEntry
        """
        _projects: dict[str, ProjectEntry] = {}

        for project in projects:
            if isinstance(project, dict):
                if "name" not in project:
                    raise KeyError("Missing name!")
                if not isinstance(project["name"], str):
                    raise TypeError(
                        f"Project name must be a string, got {type(project['name']).__name__}"
                    )
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
        remotes_from_manifest: Sequence[RemoteDict | Remote],
    ) -> tuple[dict[str, Remote], list[Remote]]:
        default_remotes: list[Remote] = []
        remotes: dict[str, Remote] = {}
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
    def from_yaml(
        text: io.TextIOWrapper | str | IO[str],
        path: str | os.PathLike[str] | None = None,
    ) -> "Manifest":
        """Create a manifest from a file like object."""
        if not isinstance(text, str):
            text = text.read()

        loaded_yaml = Manifest._load_yaml(text)

        if not loaded_yaml:
            raise RuntimeError("Manifest is not valid YAML")

        manifest = loaded_yaml["manifest"]

        if not manifest:
            raise RuntimeError("Missing manifest root element!")

        return Manifest(manifest, text=text, path=path)

    @staticmethod
    def _load_yaml(text: io.TextIOWrapper | str | IO[str]) -> Any:
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
        with open(path, encoding="utf-8", newline="") as opened_file:
            return Manifest.from_yaml(opened_file, path)

    @property
    def path(self) -> str:
        """Path to the manifest file."""
        return self.__path

    @property
    def relative_path(self) -> str:
        """Path to the manifest file relative to the current working directory."""
        return self.__relative_path

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
            [p for p in self._projects.values() if p.name in names]
            if names
            else list(self._projects.values())
        )
        self._check_all_names_found(names, projects)
        return projects

    def _check_all_names_found(
        self, names: Sequence[str], projects: Sequence[ProjectEntry]
    ) -> None:
        """Raise if any of *names* is not represented in *projects*."""
        unique_names = list(dict.fromkeys(names))  # deduplicate, preserve order
        if not unique_names or len(projects) == len(unique_names):
            return
        found = {project.name for project in projects}
        unfound = [name for name in unique_names if name not in found]
        possibles = [project.name for project in self._projects.values()]
        raise RequestedProjectNotFoundError(unfound, possibles)

    @property
    def remotes(self) -> Sequence[Remote]:
        """Get a list of Remotes from the manifest."""
        return list(self._remotes.values())

    def __repr__(self) -> str:
        """Get string representing this object."""
        return str(self._as_dict())

    def _as_dict(self) -> dict[str, ManifestDict]:
        """Get this manifest as dict."""
        remotes: Sequence[RemoteDict] = [
            remote.as_yaml() for remote in self._remotes.values()
        ]

        if len(remotes) == 1:
            remotes[0].pop("default", None)

        projects: list[dict[str, str | list[str] | dict[str, str]]] = []
        for project in self.projects:
            project_yaml: dict[str, str | list[str] | dict[str, str]] = (
                project.as_yaml()
            )
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
                self._as_dict(),
                manifest_file,
                Dumper=ManifestDumper,
                sort_keys=False,
                line_break=os.linesep,
            )

    def update_dump(self) -> None:
        """Dump the manifest to its path, using the original text as a base to preserve formatting and comments."""
        if not self.__path:
            raise RuntimeError("Cannot update dump of manifest with no path")
        if not self.__text:
            raise RuntimeError("Cannot update dump of manifest with no original text")

        updated_text = self._doc.as_yaml()

        with open(self.__path, "w", encoding="utf-8", newline="") as manifest_file:
            manifest_file.write(updated_text)

    def find_name_in_manifest(self, name: str) -> ManifestEntryLocation:
        """Find the location of a project name in the manifest.

        Raises:
            FileNotFoundError: If manifest text is not available
            RuntimeError: If the project name is not found
        """
        if not self.__text:
            raise FileNotFoundError("No manifest text available")

        for p in self._doc["manifest"]["projects"]:
            if p["name"].data == name:
                mu = p.as_marked_up()
                line_0, col_0 = mu.lc.value("name")
                return ManifestEntryLocation(
                    line_number=line_0 + 1,
                    start=col_0 + 1,
                    end=col_0 + len(name),
                )
        raise RuntimeError(f"{name} was not found in the manifest!")

    # ---------------- YAML updates ----------------
    def append_project_entry(self, project_entry: "ProjectEntry") -> None:
        """Append *project_entry* to the projects list in-memory.

        The new entry is formatted the same way as the existing YAML in the
        document (2-space indent under ``projects:``).  Call
        :meth:`update_dump` afterwards to persist the change to disk.
        """
        projects_mu = self._doc["manifest"]["projects"].as_marked_up()
        projects_mu.append(CommentedMap(project_entry.as_yaml()))
        idx = len(projects_mu) - 1
        projects_mu.ca.items[idx] = [
            None,
            [CommentToken("\n", CommentMark(0), None)],
            None,
            None,
        ]

    def update_project_version(self, project: ProjectEntry) -> None:
        """Update a project's version in the manifest in-place, preserving layout, comments, and line endings."""
        for p in self._doc["manifest"]["projects"]:
            if p["name"].data == project.name:
                mu = p.as_marked_up()
                insert_pos = 1  # right after 'name:' for any newly added key
                for key, value in project.version._asdict().items():
                    if value not in (None, ""):
                        logger.debug(
                            f"Updating {project.name} version field '{key}' to '{value}' in manifest"
                        )
                        if key in mu:
                            mu[key] = _yaml_str(value)
                        else:
                            mu.insert(insert_pos, key, _yaml_str(value))
                        insert_pos += 1
                    else:
                        # Remove any previously-pinned key that is no longer active
                        # (e.g. an old 'revision' when the project is now pinned by tag).
                        mu.pop(key, None)

                if project.integrity and project.integrity.hash:
                    mu["integrity"] = CommentedMap({"hash": project.integrity.hash})
                else:
                    # Remove a stale integrity block if the project no longer carries one.
                    mu.pop("integrity", None)
                break

        self.__text = self._doc.as_yaml()

    def check_name_uniqueness(self, project_name: str) -> None:
        """Raise if *project_name* is already used in the manifest."""
        if project_name in {project.name for project in self.projects}:
            raise ValueError(
                f"Project with name '{project_name}' already exists in manifest!"
            )

    def validate_project_name(self, name: str) -> None:
        """Raise ValueError if *name* is not valid for use in this manifest."""
        if not name:
            raise ValueError("Name cannot be empty.")
        if self._UNSAFE_NAME_RE.search(name):
            raise ValueError(
                f"Name '{name}' contains characters not allowed in a manifest name. "
                "Avoid: # : [ ] { } & * ! | > ' \" % @ `"
            )
        self.check_name_uniqueness(name)

    @staticmethod
    def validate_destination(dst: str) -> None:
        """Raise ValueError if *dst* is not a safe manifest destination path."""
        if (
            PurePosixPath(dst).is_absolute()
            or PureWindowsPath(dst).is_absolute()
            or bool(PureWindowsPath(dst).anchor)
        ):
            raise ValueError(
                f"Destination '{dst}' is an absolute path. "
                "Paths must be relative to the manifest directory."
            )
        if any(part == ".." for part in Path(dst).parts):
            raise ValueError(
                f"Destination '{dst}' contains '..'. "
                "Paths must stay within the manifest directory."
            )

    def guess_destination(self, project_name: str) -> str:
        """Guess the destination based on the common prefix of existing projects.

        With two or more existing projects the common parent directory is used.
        With a single existing project its parent directory is used (if any).
        """
        destinations = [p.destination for p in self.projects if p.destination]
        if not destinations:
            return ""
        try:
            common_path = os.path.commonpath(destinations)
        except ValueError:
            return ""
        if not common_path or common_path == os.path.sep:
            return ""
        if len(destinations) == 1:
            return Manifest._single_destination_prefix(common_path, project_name)
        return (Path(common_path) / project_name).as_posix()

    @staticmethod
    def _single_destination_prefix(common_path: str, project_name: str) -> str:
        """Return a suggested destination when only one existing project is present."""
        parent = Path(common_path).parent
        if parent != Path("."):
            return (parent / project_name).as_posix()
        return ""

    def find_remote_for_url(self, remote_url: str) -> Remote | None:
        """Return the first remote whose base URL is a prefix of *remote_url*."""
        target = remote_url.rstrip("/")
        for remote in self.remotes:
            remote_base = remote.url.rstrip("/")
            if target.startswith(remote_base):
                return remote
        return None


class ManifestDumper(yaml.SafeDumper):  # pylint: disable=too-many-ancestors
    """Dump a manifest YAML.

    HACK: insert blank lines between top-level objects
    inspired by https://stackoverflow.com/a/44284819/3786245
    """

    _last_additional_break = 0

    def write_line_break(self, data: Any = None) -> None:
        """Write a line break."""
        super().write_line_break(data)  # type: ignore[unused-ignore, no-untyped-call]

        if len(self.indents) == 2 and getattr(self.event, "value", "") != "version":
            super().write_line_break()  # type: ignore[unused-ignore, no-untyped-call]

        if len(self.indents) == 3 and self._last_additional_break != 2:
            super().write_line_break()  # type: ignore[unused-ignore, no-untyped-call]

        self._last_additional_break = len(self.indents)
