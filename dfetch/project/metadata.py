"""Metadata."""

import datetime
import os
from typing import Any

import yaml
from typing_extensions import TypedDict

import dfetch.manifest.manifest
from dfetch.project.version import Version


class Options(TypedDict):
    """Argument types for Metadata class construction."""

    last_fetch: datetime.datetime  # noqa
    branch: str
    tag: str
    revision: str
    remote_url: str
    destination: str
    hash: str


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

        self._branch: str = str(kwargs.get("branch", ""))
        self._tag: str = str(kwargs.get("tag", ""))
        self._revision: str = str(kwargs.get("revision", ""))
        self._remote_url: str = str(kwargs.get("remote_url", ""))
        self._destination: str = str(kwargs.get("destination", ""))
        self._hash: str = str(kwargs.get("hash", ""))

    @classmethod
    def from_project_entry(
        cls, project: dfetch.manifest.project.ProjectEntry
    ) -> "Metadata":
        """Create a metadata object from a project entry."""
        data: Options = {
            "branch": project.branch,
            "tag": project.tag,
            "revision": project.revision,
            "remote_url": project.remote_url,
            "destination": project.destination,
            "last_fetch": datetime.datetime(2000, 1, 1, 0, 0, 0),
            "hash": "",
        }
        return cls(data)

    @classmethod
    def from_file(cls, path: str) -> Any:
        """Load metadata file."""
        with open(path, "r") as metadata_file:
            data: Options = yaml.safe_load(metadata_file)["dfetch"]
            return cls(data)

    def fetched(self, version: Version, hash_: str = "") -> None:
        """Update metadata."""
        self._last_fetch = datetime.datetime.now()
        self._branch = version.branch
        self._tag = version.tag
        self._revision = version.revision
        self._hash = hash_

    @property
    def version(self) -> Version:
        """Get the version."""
        return Version(tag=self.tag, branch=self.branch, revision=self.revision)

    @property
    def branch(self) -> str:
        """Branch as stored in the metadata."""
        return self._branch

    @property
    def tag(self) -> str:
        """Tag as stored in the metadata."""
        return self._tag

    @property
    def revision(self) -> str:
        """Revision as stored in the metadata."""
        return self._revision

    @property
    def remote_url(self) -> str:
        """Branch as stored in the metadata."""
        return self._remote_url

    @property
    def hash(self) -> str:
        """Hash of directory."""
        return self._hash

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
                other.tag == self.tag,
                other.branch == self.branch,
                other.revision == self.revision,
                other.hash == self.hash,
            ]
        )

    def dump(self) -> None:
        """Dump metadata file to correct path."""
        metadata = {
            "dfetch": {
                "remote_url": self.remote_url,
                "branch": self.branch,
                "revision": self.revision,
                "last_fetch": self._last_fetch.strftime("%d/%m/%Y, %H:%M:%S"),
                "tag": self.tag,
                "hash": self.hash,
            }
        }

        with open(self.path, "w+") as metadata_file:
            yaml.dump(metadata, metadata_file)
