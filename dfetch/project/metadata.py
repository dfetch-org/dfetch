"""
Version Control system
"""

import os
import datetime
from typing import Any

import yaml

import dfetch.manifest.manifest


class Metadata:
    """Metadata about a single versioned control system"""

    FILENAME = ".dfetch_data.yaml"

    def __init__(
        self,
        branch: str = "",
        revision: str = "",
        remote_url: str = "",
        destination: str = "",
        last_fetch: datetime.datetime = datetime.datetime(2000, 1, 1, 0, 0, 0),
    ) -> None:
        self._last_fetch: datetime.datetime = last_fetch

        self._branch: str = branch
        self._revision: str = revision
        self._remote_url: str = remote_url
        self._destination: str = destination

    @classmethod
    def from_project_entry(
        cls, project: dfetch.manifest.project.ProjectEntry
    ) -> "Metadata":
        """ Create a metadata object from a project entry """
        return cls(
            branch=project.branch,
            revision=project.revision,
            remote_url=project.remote_url,
            destination=project.destination,
        )

    @classmethod
    def from_file(cls, path: str) -> Any:
        """ Load metadata file """
        with open(path, "r") as metadata_file:
            data = yaml.safe_load(metadata_file)["dfetch"]
            return cls(**data)

    def fetched(self, rev: str, branch: str) -> None:
        """ Update metadata """
        self._last_fetch = datetime.datetime.now()
        self._branch = branch
        self._revision = rev

    @property
    def branch(self) -> str:
        """ Branch as stored in the metadata """
        return self._branch

    @property
    def revision(self) -> str:
        """ Revision as stored in the metadata """
        return self._revision

    @property
    def remote_url(self) -> str:
        """ Branch as stored in the metadata """
        return self._remote_url

    @property
    def path(self) -> str:
        """ Path to metadata file """
        return os.path.realpath(os.path.join(self._destination, self.FILENAME))

    def __eq__(self, other: object) -> bool:
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
        """ Dump metadata file to correct path """
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
