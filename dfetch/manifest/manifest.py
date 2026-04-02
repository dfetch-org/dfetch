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
from typing_extensions import NotRequired, TypedDict

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote, RemoteDict

logger = get_logger(__name__)


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


class Manifest:
    """Manifest describing all the modules information.

    This class is created from the manifest file a project has.
    """

    CURRENT_VERSION = "0.0"

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
        if isinstance(text, (io.TextIOWrapper, IO)):
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
        with open(path, encoding="utf-8") as opened_file:
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

    def find_name_in_manifest(self, name: str) -> ManifestEntryLocation:
        """Find the location of a project name in the manifest.

        Returns:
            ManifestEntryLocation of the project name in the manifest.

        Raises:
            FileNotFoundError: If manifest text is not available
            RuntimeError: If the project name is not found in the manifest
        """
        if not self.__text:
            raise FileNotFoundError("No manifest text available")

        for line_nr, line in enumerate(self.__text.splitlines(), start=1):
            match = re.search(
                rf"^\s+-\s*name:\s*(?P<name>{re.escape(name)})\s*#?.*$", line
            )

            if match:
                return ManifestEntryLocation(
                    line_number=line_nr,
                    start=int(match.start("name")) + 1,
                    end=int(match.end("name")),
                )
        raise RuntimeError(f"{name} was not found in the manifest!")

    # Characters not allowed in a project name (YAML special chars).
    _UNSAFE_NAME_RE = re.compile(r"[\x00-\x1F\x7F-\x9F:#\[\]{}&*!|>'\"%@`]")

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
            parent_path = Path(common_path).parent
            if parent_path != Path("."):
                return (parent_path / project_name).as_posix()
            return ""

        return (Path(common_path) / project_name).as_posix()

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


def append_entry_manifest_file(
    manifest_path: str | Path,
    project_entry: ProjectEntry,
) -> None:
    """Add the project entry to the manifest file."""
    with Path(manifest_path).open("a", encoding="utf-8") as manifest_file:

        new_entry = yaml.dump(
            [project_entry.as_yaml()],
            sort_keys=False,
            line_break=os.linesep,
            indent=2,
        )
        manifest_file.write("\n")
        for line in new_entry.splitlines():
            manifest_file.write(f"  {line}\n")


def update_project_in_manifest_file(
    project: ProjectEntry,
    manifest_path: str | Path,
) -> None:
    """Update a project's version fields in the manifest file, preserving layout and comments.

    This is used when the manifest is in a version-controlled superproject: instead of
    creating a backup and regenerating the file from scratch, the existing file is edited
    in-place so that comments and formatting are retained.

    Args:
        project: The ``ProjectEntry`` whose version fields have already been updated by
            ``freeze_project()``.
        manifest_path: Path to the manifest file to update.
    """
    path = Path(manifest_path)
    text = path.read_text(encoding="utf-8")
    updated = _update_project_version_in_text(text, project)
    path.write_text(updated, encoding="utf-8")


def _yaml_scalar(value: str) -> str:
    """Return the YAML inline representation of a scalar string value.

    Strings that look like integers (e.g. SVN revision ``'176'``) are quoted so
    that YAML round-trips them back as strings.
    """
    dumped: str = yaml.dump(value, default_flow_style=None, allow_unicode=True)
    return dumped.strip()


def _find_project_block(lines: list[str], project_name: str) -> tuple[int, int, int]:
    """Return ``(start, end, item_indent)`` for the named project's YAML block.

    *start* is the index of the ``- name: <project_name>`` line.
    *end* is the exclusive end index (first line that belongs to the next block).
    *item_indent* is the column of the ``-`` character.

    Raises:
        RuntimeError: if the project name is not found.
    """
    start: int | None = None
    item_indent = 0

    for i, line in enumerate(lines):
        m = re.match(
            r"^(\s*)-\s+name:\s*" + re.escape(project_name) + r"\s*$",
            line.rstrip("\n\r"),
        )
        if m:
            start = i
            item_indent = len(m.group(1))
            break

    if start is None:
        raise RuntimeError(f"Project '{project_name}' not found in manifest text")

    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= item_indent:
            end = i
            break

    return start, end, item_indent


def _set_simple_field_in_block(
    block: list[str], field_indent: int, field_name: str, yaml_value: str
) -> list[str]:
    """Update an existing ``field_name:`` line in *block*, or insert one after the first line.

    *field_indent* is the expected column for fields in this block.
    *yaml_value* is the already-serialised YAML scalar (e.g. ``e1fda...`` or ``'176'``).
    """
    block = list(block)
    field_re = re.compile(r"^(\s+)" + re.escape(field_name) + r":\s*.*$")

    for i, line in enumerate(block):
        if field_re.match(line.rstrip("\n\r")):
            eol = "\n" if line.endswith("\n") else ""
            block[i] = " " * field_indent + field_name + ": " + yaml_value + eol
            return block

    # Field not present — insert right after the ``name:`` line (position 1).
    new_line = " " * field_indent + field_name + ": " + yaml_value + "\n"
    block.insert(1, new_line)
    return block


def _set_integrity_hash_in_block(
    block: list[str], field_indent: int, hash_value: str
) -> list[str]:
    """Update or insert ``integrity.hash`` inside *block*."""
    block = list(block)
    integrity_re = re.compile(r"^(\s+)integrity:\s*$")
    hash_re = re.compile(r"^(\s+)hash:\s*.*$")

    # Locate an existing ``integrity:`` mapping.
    integrity_line: int | None = None
    for i, line in enumerate(block):
        if integrity_re.match(line.rstrip("\n\r")):
            integrity_line = i
            break

    if integrity_line is not None:
        # Try to find an existing ``hash:`` nested inside it.
        for i in range(integrity_line + 1, len(block)):
            stripped = block[i].strip()
            if not stripped:
                continue
            if hash_re.match(block[i].rstrip("\n\r")):
                eol = "\n" if block[i].endswith("\n") else ""
                block[i] = " " * (field_indent + 2) + "hash: " + hash_value + eol
                return block
            # Stop searching once we leave the integrity sub-block.
            indent = len(block[i]) - len(block[i].lstrip())
            if indent <= field_indent:
                break
        # No ``hash:`` found — insert right after ``integrity:``.
        block.insert(
            integrity_line + 1, " " * (field_indent + 2) + "hash: " + hash_value + "\n"
        )
        return block

    # No ``integrity:`` block — append it before any trailing blank lines.
    new_lines = [
        " " * field_indent + "integrity:\n",
        " " * (field_indent + 2) + "hash: " + hash_value + "\n",
    ]
    insert_at = len(block)
    for i in range(len(block) - 1, -1, -1):
        if block[i].strip():
            insert_at = i + 1
            break
    block[insert_at:insert_at] = new_lines
    return block


def _update_project_version_in_text(text: str, project: ProjectEntry) -> str:
    """Return *text* with the version fields for *project* updated in-place.

    Only version-related fields (``revision``, ``tag``, ``branch``,
    ``integrity.hash``) are touched; all other content — including comments
    and indentation — is preserved verbatim.
    """
    project_yaml = project.as_yaml()

    # Collect simple version fields that are now set.
    fields_to_set: list[tuple[str, str]] = []
    for field in ("revision", "tag", "branch"):
        value = project_yaml.get(field)
        if value:
            fields_to_set.append((field, _yaml_scalar(str(value))))

    integrity = project_yaml.get("integrity")
    integrity_hash: str = (
        integrity["hash"]
        if isinstance(integrity, dict) and integrity.get("hash")
        else ""
    )

    if not fields_to_set and not integrity_hash:
        return text

    lines = text.splitlines(keepends=True)
    start, end, item_indent = _find_project_block(lines, project.name)
    field_indent = item_indent + 2

    block = list(lines[start:end])

    # Track which fields were inserted (not just updated) so we can keep them
    # in a sensible order right after the ``name:`` line.
    inserted: list[tuple[str, str]] = []
    for field_name, yaml_value in fields_to_set:
        field_re = re.compile(r"^(\s+)" + re.escape(field_name) + r":\s*.*$")
        found = any(field_re.match(line.rstrip("\n\r")) for line in block)
        if found:
            block = _set_simple_field_in_block(
                block, field_indent, field_name, yaml_value
            )
        else:
            inserted.append((field_name, yaml_value))

    # Insert all new fields together right after ``name:`` (position 1).
    if inserted:
        new_lines = [
            " " * field_indent + fname + ": " + val + "\n" for fname, val in inserted
        ]
        block[1:1] = new_lines

    if integrity_hash:
        block = _set_integrity_hash_in_block(block, field_indent, integrity_hash)

    return "".join(lines[:start] + block + lines[end:])
