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
from typing import IO, Any, cast

import yaml
from strictyaml import YAML, StrictYAMLError, YAMLValidationError, load
from strictyaml.ruamel.comments import CommentedMap
from strictyaml.ruamel.error import CommentMark
from strictyaml.ruamel.scalarstring import SingleQuotedScalarString
from strictyaml.ruamel.tokens import CommentToken
from typing_extensions import NotRequired, TypedDict

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote, RemoteDict
from dfetch.manifest.schema import MANIFEST_SCHEMA

logger = get_logger(__name__)


def _ensure_unique(seq: list[dict[str, Any]], key: str, context: str) -> None:
    """Raise RuntimeError if any value for *key* appears more than once in *seq*."""
    values = [item.get(key) for item in seq if key in item]
    seen: set[Any] = set()
    dups: set[Any] = set()
    for val in values:
        if val in seen:
            dups.add(val)
        else:
            seen.add(val)
    if dups:
        dup_list = ", ".join(sorted(map(str, dups)))
        raise RuntimeError(
            f"Schema validation failed:\nDuplicate {context}.{key} value(s): {dup_list}"
        )


def _normalize_value(value: Any) -> Any:
    """Recursively normalize strings in mappings and sequences."""
    if isinstance(value, str):
        return _yaml_str(value)
    if isinstance(value, dict):
        for key in list(value.keys()):
            value[key] = _normalize_value(value[key])
        return value
    if isinstance(value, list):
        for i, val in enumerate(value):
            value[i] = _normalize_value(val)
        return value
    return value


def _yaml_str(value: str) -> str | SingleQuotedScalarString:
    """Return SingleQuotedScalarString if value would be misread as non-string.

    If ``yaml.safe_load`` cannot parse *value* at all (e.g. it starts with a
    ``%`` directive marker) the value is quoted to be safe.
    """
    try:
        if not isinstance(yaml.safe_load(value), str):
            return SingleQuotedScalarString(value)
    except yaml.YAMLError:
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


class Manifest:
    """Manifest describing all the modules information.

    This class is created from the manifest file a project has.

    ``self._doc`` is the single source of truth: all state is read from and written
    to the underlying YAML document.  The only cached fields are ``__path``,
    ``__relative_path``, ``__version`` (immutable after construction), and
    ``_default_remote_name`` (also immutable: remotes are never added at runtime).
    """

    CURRENT_VERSION = "0.0"
    _UNSAFE_NAME_RE = re.compile(r"[\x00-\x1F\x7F-\x9F:#\[\]{}&*!|>'\"%@`]")

    _VERSION_KEYS: tuple[str, ...] = ("revision", "tag", "branch")

    def __init__(
        self,
        doc: YAML,
        path: str | os.PathLike[str] | None = None,
    ) -> None:
        """Create the manifest."""
        manifest_data = self._initialize_basic_attributes(doc, path)
        remotes_raw = manifest_data.get("remotes", [])
        projects_raw = manifest_data["projects"]
        self._validate_manifest_data(remotes_raw, projects_raw)
        self._setup_default_remote(remotes_raw)
        # Re-apply quoting to scalars whose style was stripped by strictyaml.
        self._normalize_string_scalars()

    def _initialize_basic_attributes(
        self, doc: YAML, path: str | os.PathLike[str] | None
    ) -> dict[str, Any]:
        """Initialize basic manifest attributes and ensure version is properly quoted.

        Args:
            doc: The parsed YAML document.
            path: Optional path to the manifest file.

        Returns:
            The manifest data dictionary.
        """
        self._doc = doc
        self.__path: str = str(path) if path else ""
        self.__relative_path: str = (
            os.path.relpath(self.__path, os.getcwd()) if self.__path else ""
        )

        manifest_data: dict[str, Any] = cast(dict[str, Any], doc.data)["manifest"]
        self.__version: str = str(manifest_data.get("version", self.CURRENT_VERSION))

        doc["manifest"].as_marked_up()["version"] = SingleQuotedScalarString(
            self.__version
        )

        return manifest_data

    def _validate_manifest_data(
        self,
        remotes_raw: list[dict[str, Any]],
        projects_raw: list[dict[str, Any]],
    ) -> None:
        """Validate that remotes and projects have unique names and destinations."""
        _ensure_unique(remotes_raw, "name", "manifest.remotes")
        _ensure_unique(projects_raw, "name", "manifest.projects")
        projects_with_effective_dst = [
            {"effective_dst": project.get("dst") or project["name"]}
            for project in projects_raw
        ]
        _ensure_unique(
            projects_with_effective_dst, "effective_dst", "manifest.projects"
        )

    def _setup_default_remote(self, remotes_raw: Sequence[RemoteDict | Remote]) -> None:
        """Determine and cache the default remote name."""
        remotes_dict, default_remotes = self._determine_remotes(remotes_raw)
        if not default_remotes:
            default_remotes = list(remotes_dict.values())[0:1]
        self._default_remote_name = (
            "" if not default_remotes else default_remotes[0].name
        )

    def _build_projects(
        self,
        projects: Sequence[
            ProjectEntryDict
            | ProjectEntry
            | dict[str, str | list[str] | dict[str, str]]
        ],
    ) -> dict[str, ProjectEntry]:
        """Build a mapping of name → ProjectEntry from raw project data.

        Args:
            projects: Iterable of project dicts or ProjectEntry objects.

        Raises:
            KeyError: A project dict is missing ``name``.
            TypeError: A project name is not a string.
            RuntimeError: A project references an unknown remote.

        Returns:
            Dict mapping project name to ProjectEntry.
        """
        remotes = {r.name: r for r in self.remotes}
        _projects: dict[str, ProjectEntry] = {}

        for project in projects:
            entry = ProjectEntry.from_raw(project, self._default_remote_name)
            _projects[entry.name] = entry
            if entry.remote:
                try:
                    entry.set_remote(remotes[entry.remote])
                except KeyError as exc:
                    raise RuntimeError(
                        f"Remote {entry.remote} of {entry.name} wasn't found "
                        f"in {list(remotes.keys())}!",
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
        try:
            doc = load(text, schema=MANIFEST_SCHEMA)
        except (YAMLValidationError, StrictYAMLError) as err:
            raise RuntimeError(
                "\n".join(
                    [
                        "Schema validation failed:",
                        "",
                        err.context_mark.get_snippet(),
                        "",
                        err.problem,
                    ]
                )
            ) from err
        except ValueError as err:
            raise RuntimeError(f"Schema validation failed: {err}") from err
        return Manifest(doc, path=path)

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
        projects_mu = self._doc["manifest"]["projects"].as_marked_up()
        return list(self._build_projects(projects_mu).values())

    @staticmethod
    def _filter_projects(
        names: Sequence[str], all_projects: Sequence[ProjectEntry]
    ) -> list[ProjectEntry]:
        """Return projects whose name appears in *names*, or all if *names* is empty."""
        if not names:
            return list(all_projects)
        return [p for p in all_projects if p.name in names]

    def selected_projects(self, names: Sequence[str]) -> Sequence[ProjectEntry]:
        """Get a list of Projects from the manifest with the given names."""
        all_projects = self.projects
        unique_names = list(dict.fromkeys(names))
        result = self._filter_projects(unique_names, all_projects)

        if not unique_names or len(result) == len(unique_names):
            return result

        found = {project.name for project in result}

        raise RequestedProjectNotFoundError(
            unfound=[name for name in unique_names if name not in found],
            possibles=[project.name for project in all_projects],
        )

    @property
    def remotes(self) -> Sequence[Remote]:
        """Get a list of Remotes from the manifest."""
        manifest_mu = self._doc["manifest"].as_marked_up()
        remotes_dict, _ = self._determine_remotes(manifest_mu.get("remotes", []))
        return list(remotes_dict.values())

    def __repr__(self) -> str:
        """Get string representing this object."""
        return str(self._doc.as_yaml())

    def dump(self, path: str | None = None) -> None:
        """Write the manifest to *path*, preserving formatting and comments.

        If *path* is omitted the manifest is written back to the file it was
        loaded from.  Raises ``RuntimeError`` if no path is available.
        """
        target = path or self.__path
        if not target:
            raise RuntimeError("Cannot dump manifest with no path")
        # Re-normalize string scalars to ensure newly added/modified entries
        # (e.g., from append_project_entry or update_project_version) are
        # properly quoted before serializing.
        self._normalize_string_scalars()
        with open(target, "w", encoding="utf-8", newline="") as manifest_file:
            manifest_file.write(self._doc.as_yaml())

    def find_name_in_manifest(self, name: str) -> ManifestEntryLocation:
        """Find the location of a project name in the manifest.

        Raises:
            FileNotFoundError: If manifest text is not available
            RuntimeError: If the project name is not found
        """
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
    def _normalize_string_scalars(self) -> None:
        """Re-apply ``SingleQuotedScalarString`` to any string that would be misread.

        strictyaml strips quoting-style information during schema validation, so
        a value like ``'176'`` (single-quoted in the source YAML) becomes a plain
        Python ``str`` in the ruamel layer.  ruamel then serialises it without
        quotes, producing the integer ``176``.  We walk all string fields in every
        project and remote entry (including nested strings in mappings and sequences)
        and restore the quoting wherever ``_yaml_str`` determines it is needed.
        """
        manifest_mu = self._doc["manifest"].as_marked_up()
        for entry in manifest_mu.get("projects", []):
            for key in list(entry.keys()):
                entry[key] = _normalize_value(entry[key])
        for entry in manifest_mu.get("remotes", []):
            for key in list(entry.keys()):
                entry[key] = _normalize_value(entry[key])

    def append_project_entry(self, project_entry: "ProjectEntry") -> None:
        """Append *project_entry* to the projects list in-memory.

        The new entry is formatted the same way as the existing YAML in the
        document (2-space indent under ``projects:``).  Call
        :meth:`dump` afterwards to persist the change to disk.
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


class ManifestBuilder:
    """Builds a new manifest YAML document from scratch with correct blank-line formatting.

    Use this when creating a manifest from scratch (e.g. ``dfetch import``).
    For loading and modifying existing manifests use :class:`Manifest` directly.
    """

    def __init__(self) -> None:
        """Create an empty builder."""
        self._remotes: list[Remote] = []
        self._project_dicts: list[dict[str, Any]] = []

    def add_remote(self, remote: Remote) -> "ManifestBuilder":
        """Add a remote entry."""
        self._remotes.append(remote)
        return self

    def add_project_dict(self, project: dict[str, Any]) -> "ManifestBuilder":
        """Add a project entry as a plain dict (as returned by ``ProjectEntry.as_yaml()``)."""
        self._project_dicts.append(project)
        return self

    def build(self) -> "Manifest":
        """Render and load the manifest."""
        return Manifest.from_yaml(self._render())

    def _render(self) -> str:
        """Produce a correctly-formatted YAML string for the manifest."""
        data: dict[str, Any] = {"manifest": {"version": "0.0"}}
        if self._remotes:
            data["manifest"]["remotes"] = [r.as_yaml() for r in self._remotes]
        data["manifest"]["projects"] = self._project_dicts

        raw = yaml.dump(data, sort_keys=False)

        # Insert a blank line before the remotes: and projects: section headers.
        raw = re.sub(r"\n(  (?:remotes|projects):)", r"\n\n\1", raw)

        # Insert a blank line between consecutive entries in each section.
        # re.split with a capturing group keeps the delimiters in the list, so
        # every even index ≥ 2 is a section body that can be substituted
        # independently without one pass's changes affecting the next.
        parts = re.split(r"(\n  (?:remotes|projects):\n)", raw)
        for i in range(2, len(parts), 2):
            parts[i] = re.sub(r"\n(  - )", r"\n\n\1", parts[i])
        raw = "".join(parts)

        return raw
