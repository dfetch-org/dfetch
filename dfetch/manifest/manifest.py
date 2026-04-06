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
from strictyaml.ruamel.comments import CommentedMap, CommentedSeq
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


def _ensure_blank_line_after_nested_map(parent: CommentedMap, key: str) -> None:
    """Ensure a blank line appears after a nested mapping value.

    For a block mapping value (e.g. ``integrity:`` with sub-key ``hash:``),
    the blank line must live inside the nested map — at
    ``nested.ca.items[last_key][2]`` — not on the parent key.  Putting it on
    the parent key at position ``[2]`` or ``[3]`` lands it *between* the key
    line and the first sub-key, producing a spurious blank line.
    """
    # Clear any spurious blanks the parent map may carry on positions [2]/[3].
    parent_items = parent.ca.items.get(key)
    if parent_items:
        if parent_items[2] is not None:
            parent_items[2] = None
        if parent_items[3] is not None:
            parent_items[3] = None

    nested: CommentedMap = parent[key]
    nested_keys = list(nested.keys())
    if nested_keys:
        _ensure_blank_line_after(nested, nested_keys[-1])


def _ensure_blank_line_after_seq(seq: CommentedSeq) -> None:
    """Ensure there is a blank line after the last item of *seq*.

    The blank line belongs at ``seq.ca.items[last_idx][0]`` (the pre-comment
    slot of the last element).  We also clear any extra newline stored at
    ``seq.ca.items[0][1]``, which is where ruamel parks whitespace between the
    parent key (e.g. ``patch:``) and the first ``-`` item — the source of the
    spurious blank line that this function is designed to prevent.
    """
    if not seq:
        return

    # Clear spurious blank line between the key and the first list item.
    first_item_ca = seq.ca.items.get(0)
    if first_item_ca is not None and first_item_ca[1] is not None:
        first_item_ca[1] = None

    # Ensure blank line after the last item for project-entry separation.
    last_idx = len(seq) - 1
    existing = seq.ca.items.get(last_idx, [None, None, None, None])
    token = existing[0]
    if token is None:
        existing[0] = CommentToken("\n\n", CommentMark(0), None)
        seq.ca.items[last_idx] = existing
    elif not token.value.endswith("\n\n"):
        token.value = token.value.rstrip("\n") + "\n\n"


def _ensure_blank_line_after(ca_map: CommentedMap, key: str) -> None:
    """Ensure there is exactly one blank line after *key*'s value in *ca_map*.

    Blank lines in ruamel are stored as trailing ``CommentToken`` values at
    position ``[2]`` of ``ca_map.ca.items[key]``.  If no token exists one is
    created; if one already exists its trailing newlines are normalised to two
    (the line ending of the value itself plus the blank line).
    """
    items = ca_map.ca.items.get(key, [None, None, None, None])
    token = items[2]
    if token is None:
        items[2] = CommentToken("\n\n", CommentMark(0), None)
        ca_map.ca.items[key] = items
    elif not token.value.endswith("\n\n"):
        token.value = token.value.rstrip("\n") + "\n\n"


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
        self._doc = doc
        self.__path: str = str(path) if path else ""
        self.__relative_path: str = (
            os.path.relpath(self.__path, os.getcwd()) if self.__path else ""
        )

        manifest_data: dict[str, Any] = cast(dict[str, Any], doc.data)["manifest"]
        self.__version: str = str(manifest_data.get("version", self.CURRENT_VERSION))

        # Ensure version is always written as a quoted string by dump().
        doc["manifest"].as_marked_up()["version"] = SingleQuotedScalarString(
            self.__version
        )

        remotes_raw = manifest_data.get("remotes", [])
        projects_raw = manifest_data["projects"]

        _ensure_unique(remotes_raw, "name", "manifest.remotes")
        _ensure_unique(projects_raw, "name", "manifest.projects")
        _ensure_unique(projects_raw, "dst", "manifest.projects")

        # Determine and cache the default remote name (remotes don't change at runtime).
        remotes_dict, default_remotes = self._determine_remotes(remotes_raw)
        if not default_remotes:
            default_remotes = list(remotes_dict.values())[0:1]
        self._default_remote_name = (
            "" if not default_remotes else default_remotes[0].name
        )

        # Ensure blank lines appear before 'remotes:' and 'projects:' when dumped.
        self._ensure_section_spacing()

        # Re-apply quoting to scalars whose style was stripped by strictyaml.
        self._normalize_string_scalars()

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
        quotes, producing the integer ``176``.  We walk all top-level string
        fields in every project and remote entry and restore the quoting wherever
        ``_yaml_str`` determines it is needed.
        """
        manifest_mu = self._doc["manifest"].as_marked_up()
        for entry in manifest_mu.get("projects", []):
            for key in list(entry.keys()):
                if isinstance(entry[key], str):
                    entry[key] = _yaml_str(entry[key])
        for entry in manifest_mu.get("remotes", []):
            for key in list(entry.keys()):
                if isinstance(entry[key], str):
                    entry[key] = _yaml_str(entry[key])

    def _ensure_section_spacing(self) -> None:
        """Ensure blank lines appear before ``remotes:`` and ``projects:`` and between entries."""
        manifest_mu = self._doc["manifest"].as_marked_up()
        _ensure_blank_line_after(manifest_mu, "version")

        remotes_mu = manifest_mu.get("remotes")
        if remotes_mu:
            last_remote = remotes_mu[-1]
            _ensure_blank_line_after(last_remote, list(last_remote.keys())[-1])

        projects_mu = manifest_mu.get("projects", [])
        for project in projects_mu[:-1]:  # all entries except the last
            last_key = list(project.keys())[-1]
            value = project[last_key]
            if isinstance(value, CommentedSeq):
                # Clear any spurious blank line that ended up between the key
                # and the first list item (stored at ca.items[key][2] in the
                # parent map), then place the blank line after the last item.
                key_items = project.ca.items.get(last_key)
                if key_items and key_items[2] is not None:
                    key_items[2] = None
                _ensure_blank_line_after_seq(value)
            elif isinstance(value, CommentedMap):
                _ensure_blank_line_after_nested_map(project, last_key)
            else:
                _ensure_blank_line_after(project, last_key)

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
