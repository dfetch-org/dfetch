"""Metadata."""

import datetime
import os
from dataclasses import dataclass
from typing import Iterable, Optional

import yaml
from typing_extensions import TypedDict

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version

DONT_EDIT_WARNING = """\
# This is a generated file by dfetch. Don't edit this, but edit the manifest.
# For more info see https://dfetch.rtfd.io/en/latest/getting_started.html
"""


@dataclass
class FileInfo:
    """Information about a single fetched file."""

    path: str
    hash: str
    permissions: str  # octal

    def __repr__(self) -> str:
        return f"{self.path.replace("|", r"\|")}|{self.hash}|{self.permissions}"

    @staticmethod
    def from_list(data: Iterable[str]) -> Iterable["FileInfo"]:
        """Create a list of FileInfo's from a string"""
        parsed = []
        for entry in data:
            path, hash_digest, permissions = (
                entry.split("|", maxsplit=3) + ["", "", ""]
            )[:3]
            parsed.append(FileInfo(path, hash_digest, permissions.zfill(3)))
        return parsed


class Options(TypedDict):  # pylint: disable=too-many-ancestors
    """Argument types for Metadata class construction."""

    last_fetch: datetime.datetime  # noqa
    branch: str
    tag: str
    revision: str
    remote_url: str
    destination: str
    hash: str
    patch: str
    files: Optional[Iterable[FileInfo]] = None


class Metadata:
    """Metadata about a single versioned control system."""

    BASENAME = ".dfetch_data"
    EXT = "yaml"
    FILENAME = f"{BASENAME}.{EXT}"

    def __init__(self, kwargs: Options) -> None:
        """Create the metadata."""
        self._last_fetch: datetime.datetime = kwargs.get(
            "last_fetch", datetime.datetime(2000, 1, 1, 0, 0, 0)
        )

        self._version: Version = Version(
            branch=str(kwargs.get("branch", "")),
            tag=str(kwargs.get("tag", "")),
            revision=str(kwargs.get("revision", "")),
        )
        self._remote_url: str = str(kwargs.get("remote_url", ""))
        self._destination: str = str(kwargs.get("destination", ""))
        self._hash: str = str(kwargs.get("hash", ""))
        self._patch: str = str(kwargs.get("patch", ""))
        self._files: Optional[Iterable[FileInfo]] = FileInfo.from_list(
            kwargs.get("files", [])
        )

    @classmethod
    def from_project_entry(cls, project: ProjectEntry) -> "Metadata":
        """Create a metadata object from a project entry."""
        data: Options = {
            "branch": project.branch,
            "tag": project.tag,
            "revision": project.revision,
            "remote_url": project.remote_url,
            "destination": project.destination,
            "last_fetch": datetime.datetime(2000, 1, 1, 0, 0, 0),
            "hash": "",
            "patch": project.patch,
            "files": [],
        }
        return cls(data)

    @classmethod
    def from_file(cls, path: str) -> "Metadata":
        """Load metadata file."""
        with open(path, "r", encoding="utf-8") as metadata_file:
            data: Options = yaml.safe_load(metadata_file)["dfetch"]
            return cls(data)

    def fetched(
        self,
        version: Version,
        hash_: str = "",
        patch_: str = "",
        files: Optional[Iterable[FileInfo]] = None,
    ) -> None:
        """Update metadata."""
        self._last_fetch = datetime.datetime.now()
        self._version = version
        self._hash = hash_
        self._patch = patch_
        self._files = files

    @property
    def version(self) -> Version:
        """Get the version."""
        return self._version

    @property
    def branch(self) -> str:
        """Branch as stored in the metadata."""
        return self._version.branch

    @property
    def tag(self) -> str:
        """Tag as stored in the metadata."""
        return self._version.tag

    @property
    def revision(self) -> str:
        """Revision as stored in the metadata."""
        return self._version.revision

    @property
    def remote_url(self) -> str:
        """Remote url as stored in the metadata."""
        return self._remote_url

    @property
    def last_fetch(self) -> datetime.datetime:
        """Last fetch as stored in the metadata."""
        return self._last_fetch

    def last_fetch_string(self) -> str:
        """Last fetch as stored in the metadata (converted to string)."""
        return self._last_fetch.strftime("%d/%m/%Y, %H:%M:%S")

    @property
    def hash(self) -> str:
        """Hash of directory as stored in the metadata.."""
        return self._hash

    @property
    def patch(self) -> str:
        """The applied patch as stored in the metadata."""
        return self._patch

    @property
    def path(self) -> str:
        """Path to metadata file."""
        if os.path.isdir(self._destination):
            return os.path.realpath(os.path.join(self._destination, self.FILENAME))

        filename = f"{self.BASENAME}-{os.path.basename(self._destination)}.{self.EXT}"
        return os.path.realpath(
            os.path.join(os.path.dirname(self._destination), filename)
        )

    def __eq__(self, other: object) -> bool:
        """Check if other object is the same."""
        if not isinstance(other, Metadata):
            return NotImplemented
        return all(
            [
                other.remote_url == self.remote_url,
                other._version.tag == self._version.tag,
                other._version.branch == self._version.branch,
                other._version.revision == self._version.revision,
                other.hash == self.hash,
                other.patch == self.patch,
                other._files == self._files,
            ]
        )

    def dump(self) -> None:
        """Dump metadata file to correct path."""
        metadata = {
            "dfetch": {
                "remote_url": self.remote_url,
                "branch": self._version.branch,
                "revision": self._version.revision,
                "last_fetch": self.last_fetch_string(),
                "tag": self._version.tag,
                "hash": self.hash,
                "patch": self.patch,
                "files": [str(info) for info in self._files or []],
            }
        }

        with open(self.path, "w+", encoding="utf-8") as metadata_file:
            metadata_file.write(DONT_EDIT_WARNING)
            yaml.dump(metadata, metadata_file)
