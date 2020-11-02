"""Version Control system."""

import logging
import os
from abc import ABC, abstractmethod

from colorama import Fore

import dfetch.manifest.manifest
from dfetch.project.metadata import Metadata
from dfetch.util.util import safe_rmtree


class VCS(ABC):
    """Abstract Version Control System object.

    This object represents one Project entry in the Manifest.
    It can be updated.
    """

    def __init__(
        self, project: dfetch.manifest.project.ProjectEntry, logger: logging.Logger
    ) -> None:
        """Create the VCS."""
        self._logger = logger
        self._project = project
        self._metadata = Metadata.from_project_entry(self._project)

    def update(self) -> None:
        """Update this VCS if required."""
        if not (self._metadata.branch and self._metadata.revision):
            self._update_metadata()

        if not self._update_required():
            return

        if os.path.exists(self.local_path):
            self.logger.debug(f"Clearing destination directory {self.local_path}")
            safe_rmtree(self.local_path)

        self.logger.debug(
            f"fetching {self._project.name} {self._project.revision} from {self._project.remote_url}"
        )

        self._fetch_impl()
        self._metadata.fetched(self.revision, self.branch)

        self.logger.debug(f"Writing repo metadata to: {self._metadata.path}")
        self._metadata.dump()

    def check_for_update(self) -> None:
        """Check if there is an update available."""
        on_disk_revision: str = ""
        if os.path.exists(self.local_path) and os.path.exists(self._metadata.path):
            on_disk = Metadata.from_file(self._metadata.path)
            on_disk_revision = on_disk.revision

        remote_revision = self._check_impl()

        if not on_disk_revision:
            self._log_project(f"available ({remote_revision[:8]})")
        elif remote_revision[:8] == on_disk_revision[:8]:
            self._log_project(f"up-to-date ({on_disk.branch} - {on_disk_revision[:8]})")
        else:
            pinned: str = (
                "and pinned "
                if self._project.revision[:8] == on_disk_revision[:8]
                else ""
            )
            self._log_project(
                f"installed {pinned}({on_disk.branch} - {on_disk_revision[:8]}), available ({remote_revision[:8]})"
            )

    def _update_required(self) -> bool:

        wanted_version_string = (
            f"({self._metadata.branch} - {self._metadata.revision[:8]})"
        )
        if os.path.exists(self.local_path) and os.path.exists(self._metadata.path):

            on_disk = Metadata.from_file(self._metadata.path)
            if self._metadata != on_disk:
                self._log_project(
                    f"updating ({on_disk.branch} - {on_disk.revision[:8]})"
                    f" --> {wanted_version_string}",
                )
                return True
            self._log_project(f"up-to-date {wanted_version_string}")
            return False
        self._log_project(
            f"fetching {wanted_version_string}",
        )
        return True

    def _log_project(self, msg: str) -> None:
        self.logger.info(f"  {Fore.GREEN}- {self._project.name:20s}:{Fore.BLUE} {msg}")

    @property
    def local_path(self) -> str:
        """Get the local destination of this project."""
        return self._project.destination

    @property
    def branch(self) -> str:
        """Get the required branch of this VCS."""
        return self._metadata.branch

    @property
    def revision(self) -> str:
        """Get the required revision of this VCS."""
        return self._metadata.revision

    @property
    def remote(self) -> str:
        """Get the remote URL of this VCS."""
        return self._metadata.remote_url

    @property
    def logger(self) -> logging.Logger:
        """Return the logger for this VCS."""
        return self._logger

    @abstractmethod
    def check(self) -> bool:
        """Check if it can handle the type."""

    @abstractmethod
    def _check_impl(self) -> str:
        """Check the given version of the VCS, should be implemented by the child class."""

    @abstractmethod
    def _fetch_impl(self) -> None:
        """Fetch the given version of the VCS, should be implemented by the child class."""

    @abstractmethod
    def _update_metadata(self) -> None:
        """Update the metadata after performing a fetch."""
