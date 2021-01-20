"""Metadata."""

import datetime
import os
from typing import Any

import yaml
from typing_extensions import TypedDict

import dfetch.manifest.manifest


class Options(TypedDict):
    """Argument types for Metadata class construction."""

    last_fetch: datetime.datetime  # noqa
    branch: str
    revision: str
    remote_url: str
    destination: str


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
        self._revision: str = str(kwargs.get("revision", ""))
        self._remote_url: str = str(kwargs.get("remote_url", ""))
        self._destination: str = str(kwargs.get("destination", ""))

    @classmethod
    def from_project_entry(
        cls, project: dfetch.manifest.project.ProjectEntry
    ) -> "Metadata":
        """Create a metadata object from a project entry."""
        data: Options = {
            "branch": project.branch,
            "revision": project.revision,
            "remote_url": project.remote_url,
            "destination": project.destination,
            "last_fetch": datetime.datetime(2000, 1, 1, 0, 0, 0),
        }
        return cls(data)

    @classmethod
    def from_file(cls, path: str) -> Any:
        """Load metadata file."""
        with open(path, "r") as metadata_file:
            data: Options = yaml.safe_load(metadata_file)["dfetch"]
            return cls(data)

    def fetched(self, rev: str, branch: str) -> None:
        """Update metadata."""
        self._last_fetch = datetime.datetime.now()
        self._branch = branch
        self._revision = rev

    @property
    def branch(self) -> str:
        """Branch as stored in the metadata."""
        return self._branch

    @property
    def revision(self) -> str:
        """Revision as stored in the metadata."""
        return self._revision

    @property
    def remote_url(self) -> str:
        """Branch as stored in the metadata."""
        return self._remote_url

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
                other.branch == self.branch,
                other.revision == self.revision,
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
            }
        }

        with open(self.path, "w+") as metadata_file:
            yaml.dump(metadata, metadata_file)
