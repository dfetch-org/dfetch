"""Version Control system."""

import os
from abc import ABC, abstractmethod

import dfetch.manifest.manifest
from dfetch.log import get_logger
from dfetch.project.metadata import Metadata
from dfetch.util.util import safe_rm

logger = get_logger(__name__)


class VCS(ABC):
    """Abstract Version Control System object.

    This object represents one Project entry in the Manifest.
    It can be updated.
    """

    NAME = ""

    def __init__(self, project: dfetch.manifest.project.ProjectEntry) -> None:
        """Create the VCS."""
        self._project = project
        self._metadata = Metadata.from_project_entry(self._project)

    def update(self) -> None:
        """Update this VCS if required."""
        if not (self._metadata.branch and self._metadata.revision):
            self._update_metadata()

        if not self._update_required():
            return

        if os.path.exists(self.local_path):
            logger.debug(f"Clearing destination {self.local_path}")
            safe_rm(self.local_path)

        logger.debug(
            f"fetching {self._project.name} {self._project.revision} from {self._project.remote_url}"
        )

        self._fetch_impl()
        self._metadata.fetched(self.revision, self.branch)

        logger.debug(f"Writing repo metadata to: {self._metadata.path}")
        self._metadata.dump()

    def check_for_update(self) -> None:
        """Check if there is an update available."""
        on_disk_revision: str = ""
        if os.path.exists(self.local_path) and os.path.exists(self._metadata.path):
            on_disk = Metadata.from_file(self._metadata.path)
            on_disk_revision = on_disk.revision

        remote_revision = self._check_impl()

        if not on_disk_revision:
            self._log_project(f"available ({remote_revision})")
        elif remote_revision == on_disk_revision:
            self._log_project(f"up-to-date ({on_disk.branch} - {on_disk_revision})")
        else:
            pinned: str = (
                "and pinned " if self._project.revision == on_disk_revision else ""
            )
            self._log_project(
                f"installed {pinned}({on_disk.branch} - {on_disk_revision}), available ({remote_revision})"
            )

    def _update_required(self) -> bool:

        wanted_version_string = f"({self._metadata.branch} - {self._metadata.revision})"
        if os.path.exists(self.local_path) and os.path.exists(self._metadata.path):

            on_disk = Metadata.from_file(self._metadata.path)
            if self._metadata != on_disk:
                self._log_project(
                    f"updating ({on_disk.branch} - {on_disk.revision})"
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
        logger.print_info_line(self._project.name, msg)

    @staticmethod
    def _log_tool(name: str, msg: str) -> None:
        logger.print_info_line(name, msg.strip())

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

    @abstractmethod
    def check(self) -> bool:
        """Check if it can handle the type."""

    @staticmethod
    @abstractmethod
    def list_tool_info() -> None:
        """Print out version information."""

    @abstractmethod
    def _check_impl(self) -> str:
        """Check the given version of the VCS, should be implemented by the child class."""

    @abstractmethod
    def _fetch_impl(self) -> None:
        """Fetch the given version of the VCS, should be implemented by the child class."""

    @abstractmethod
    def _update_metadata(self) -> None:
        """Update the metadata after performing a fetch."""
