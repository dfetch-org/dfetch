"""Version Control system."""

import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import dfetch.manifest.manifest
from dfetch.log import get_logger
from dfetch.project.metadata import Metadata
from dfetch.project.version import Version
from dfetch.util.util import hash_directory, safe_rm

logger = get_logger(__name__)


class VCS(ABC):
    """Abstract Version Control System object.

    This object represents one Project entry in the Manifest.
    It can be updated.
    """

    NAME = ""
    DEFAULT_BRANCH = ""

    def __init__(self, project: dfetch.manifest.project.ProjectEntry) -> None:
        """Create the VCS."""
        self._project = project
        self._metadata = Metadata.from_project_entry(self._project)

    def check_wanted_with_local(self) -> Tuple[Optional[Version], Optional[Version]]:
        """Given the project entry in the manifest, get the relevant version from disk

        Returns:
            Tuple[Optional[Version], Optional[Version]]: Wanted, Have
        """
        if os.path.exists(self.local_path) and os.path.exists(self._metadata.path):
            on_disk = Metadata.from_file(self._metadata.path).version

            if on_disk.tag and on_disk.tag == self._metadata.tag:
                return (Version(tag=self._metadata.tag), Version(tag=on_disk.tag))

            if on_disk.revision and on_disk.revision == self._metadata.revision:
                if self.revision_is_enough():
                    return (
                        Version(revision=self._metadata.revision),
                        Version(revision=on_disk.revision),
                    )

                if self._metadata.branch and self._metadata.branch in [
                    on_disk.branch,
                    self.DEFAULT_BRANCH,
                ]:
                    return (
                        Version(
                            revision=self._metadata.revision,
                            branch=self._metadata.branch,
                        ),
                        Version(
                            revision=on_disk.revision,
                            branch=on_disk.branch or self.DEFAULT_BRANCH,
                        ),
                    )

            # Branch only
            if not on_disk.tag and not self._metadata.revision:
                branch = self._metadata.branch or self.DEFAULT_BRANCH
                latest_revision = self._latest_revision_on_branch(branch)

                return (
                    Version(revision=latest_revision, branch=branch),
                    Version(revision=on_disk.revision, branch=on_disk.branch),
                )

        return (
            Version(
                tag=self._metadata.tag,
                branch=self._metadata.branch,
                revision=self._metadata.revision,
            ),
            None,
        )

    def update_is_required(self) -> bool:
        """Check if this project should be upgraded."""
        wanted, current = self.check_wanted_with_local()

        if wanted == current:
            logger.print_info_line(self._project.name, f"up-to-date ({current})")
            return False

        logger.debug(self._project.name, f"Current ({current}), Available ({wanted})")
        return True

    def update(self) -> None:
        """Update this VCS if required."""
        if not self.update_is_required():
            return

        if os.path.exists(self.local_path):
            logger.debug(f"Clearing destination {self.local_path}")
            safe_rm(self.local_path)

        to_fetch = self._determine_version_to_fetch()

        actually_fetched = self._fetch_impl(to_fetch)
        logger.print_info_line(self._project.name, f"Fetched {actually_fetched}")
        self._metadata.fetched(actually_fetched)

        logger.debug(f"Writing repo metadata to: {self._metadata.path}")
        self._metadata.dump()

        logger.info(hash_directory(self.local_path, skiplist=[self._metadata.FILENAME]))

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

    def _determine_version_to_fetch(self) -> Version:

        if self._metadata.tag:
            return Version(tag=self._metadata.tag)

        return Version(
            revision=self._metadata.revision,
            branch=""
            if self.revision_is_enough()
            else self._metadata.branch or self.DEFAULT_BRANCH,
        )

    def _update_required(self) -> bool:

        wanted_version_string = self._metadata.tag or " - ".join(
            [self._metadata.branch, self._metadata.revision]
        )
        wanted_version_string = f"({wanted_version_string})"
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
    def tag(self) -> str:
        """Get the required tag of this VCS."""
        return self._metadata.tag

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
    def revision_is_enough() -> bool:
        """See if this VCS can uniquely distinguish branch with revision only."""

    @abstractmethod
    def _latest_revision_on_branch(self, branch: str) -> str:
        """Get the latest revision on a branch."""

    @staticmethod
    @abstractmethod
    def list_tool_info() -> None:
        """Print out version information."""

    @abstractmethod
    def _check_impl(self) -> str:
        """Check the given version of the VCS, should be implemented by the child class."""

    @abstractmethod
    def _fetch_impl(self, version: Version) -> Version:
        """Fetch the given version of the VCS, should be implemented by the child class."""
