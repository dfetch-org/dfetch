"""Version Control system."""

import fnmatch
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from patch_ng import fromfile

import dfetch.manifest.manifest
from dfetch.log import get_logger
from dfetch.manifest.version import Version
from dfetch.project.metadata import Metadata
from dfetch.util.util import hash_directory, safe_rm
from dfetch.util.versions import latest_tag_from_list

logger = get_logger(__name__)


class VCS(ABC):
    """Abstract Version Control System object.

    This object represents one Project entry in the Manifest.
    It can be updated.
    """

    NAME = ""
    DEFAULT_BRANCH = ""
    LICENSE_GLOBS = ["licen[cs]e*", "copying*", "copyright*"]

    def __init__(self, project: dfetch.manifest.project.ProjectEntry) -> None:
        """Create the VCS."""
        self.__project = project
        self.__metadata = Metadata.from_project_entry(self.__project)

    def check_wanted_with_local(self) -> Tuple[Optional[Version], Optional[Version]]:
        """Given the project entry in the manifest, get the relevant version from disk.

        Returns:
            Tuple[Optional[Version], Optional[Version]]: Wanted, Have
        """
        on_disk = self.on_disk_version()

        if not on_disk:
            return (self.wanted_version, None)

        if self.wanted_version.tag:
            return (Version(tag=self.wanted_version.tag), Version(tag=on_disk.tag))

        wanted_branch, on_disk_branch = "", ""
        if not (self.wanted_version.revision and self.revision_is_enough()):
            wanted_branch = self.wanted_version.branch or self.DEFAULT_BRANCH
            on_disk_branch = on_disk.branch

        wanted_revision = (
            self.wanted_version.revision
            or self._latest_revision_on_branch(wanted_branch)
        )

        return (
            Version(
                revision=wanted_revision,
                branch=wanted_branch,
            ),
            Version(revision=on_disk.revision, branch=on_disk_branch),
        )

    def update_is_required(self, force: bool = False) -> Optional[Version]:
        """Check if this project should be upgraded.

        Args:
            force (bool, optional): Ignore if versions match.
                                    Defaults to False.
        """
        wanted, current = self.check_wanted_with_local()

        if not force and wanted == current:
            self._log_project(f"up-to-date ({current})")
            return None

        logger.debug(f"{self.__project.name} Current ({current}), Available ({wanted})")
        return wanted

    def update(self, force: bool = False) -> None:
        """Update this VCS if required.

        Args:
            force (bool, optional): Ignore if version is ok or any local changes were done.
                                    Defaults to False.
        """
        to_fetch = self.update_is_required(force)

        if not to_fetch:
            return

        if not force and self._are_there_local_changes():
            self._log_project(
                "skipped - local changes after last update (use --force to overwrite)"
            )
            return

        if os.path.exists(self.local_path):
            logger.debug(f"Clearing destination {self.local_path}")
            safe_rm(self.local_path)

        actually_fetched = self._fetch_impl(to_fetch)
        self._log_project(f"Fetched {actually_fetched}")

        applied_patch = ""
        if self.__project.patch:
            if os.path.exists(self.__project.patch):
                self.apply_patch()
                applied_patch = self.__project.patch
            else:
                logger.warning(f"Skipping non-existent patch {self.__project.patch}")

        self.__metadata.fetched(
            actually_fetched,
            hash_=hash_directory(self.local_path, skiplist=[self.__metadata.FILENAME]),
            patch_=applied_patch,
        )

        logger.debug(f"Writing repo metadata to: {self.__metadata.path}")
        self.__metadata.dump()

    def apply_patch(self) -> None:
        """Apply the specified patch to the destination."""
        patch_set = fromfile(self.__project.patch)

        if patch_set:
            if patch_set.apply(0, root=self.__project.destination, fuzz=True):
                self._log_project(f'Applied path "{self.__project.patch}"')
            else:
                raise RuntimeError(f'Applying path "{self.__project.patch}" failed')
        else:
            raise RuntimeError(f'Invalid patch file: "{self.__project.patch}"')

    def check_for_update(self) -> None:
        """Check if there is an update available."""
        on_disk_version = self.on_disk_version()
        latest_version = self._check_for_newer_version()

        if not on_disk_version:
            wanted = (
                f"wanted ({self.wanted_version}), " if any(self.wanted_version) else ""
            )
            self._log_project(f"{wanted}available ({latest_version})")
        elif latest_version == on_disk_version:
            self._log_project(f"up-to-date ({latest_version})")
        elif on_disk_version == self.wanted_version:
            self._log_project(
                f"wanted & current ({on_disk_version}), available ({latest_version})"
            )
        else:
            self._log_project(
                f"wanted ({str(self.wanted_version) or 'latest'}), "
                f"current ({on_disk_version}), available ({latest_version})"
            )

    def _log_project(self, msg: str) -> None:
        logger.print_info_line(self.__project.name, msg)

    @staticmethod
    def _log_tool(name: str, msg: str) -> None:
        logger.print_info_line(name, msg.strip())

    @property
    def local_path(self) -> str:
        """Get the local destination of this project."""
        return self.__project.destination

    @property
    def wanted_version(self) -> Version:
        """Get the wanted version of this VCS."""
        return self.__metadata.version

    @property
    def metadata_path(self) -> str:
        """Get the path of the metadata."""
        return self.__metadata.path

    @property
    def remote(self) -> str:
        """Get the remote URL of this VCS."""
        return self.__metadata.remote_url

    @property
    def source(self) -> str:
        """Get the source folder of this VCS."""
        return self.__project.source

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

    @abstractmethod
    def _list_of_tags(self) -> List[str]:
        """Get list of all available tags."""

    @staticmethod
    @abstractmethod
    def list_tool_info() -> None:
        """Print out version information."""

    def on_disk_version(self) -> Optional[Version]:
        """Get the version of the project on disk.

        Returns:
            Version: Could be None of no on disk version
        """
        return (
            None
            if not os.path.exists(self.__metadata.path)
            else Metadata.from_file(self.__metadata.path).version
        )

    def _on_disk_hash(self) -> Optional[str]:
        """Get the hash of the project on disk.

        Returns:
            Str: Could be None if no on disk version
        """
        return (
            None
            if not os.path.exists(self.__metadata.path)
            else Metadata.from_file(self.__metadata.path).hash
        )

    def _check_for_newer_version(self) -> Version:
        """Check if a newer version is available on the given branch."""
        if self.wanted_version.tag:
            return Version(
                tag=latest_tag_from_list(self.wanted_version.tag, self._list_of_tags())
            )
        if self.wanted_version.branch == " ":
            branch = ""
        else:
            branch = self.wanted_version.branch or self.DEFAULT_BRANCH
        return Version(revision=self._latest_revision_on_branch(branch), branch=branch)

    def _are_there_local_changes(self) -> bool:
        """Check if there are local changes.

        Returns:
          Bool: True if there are local changes, false if no were detected or no hash was found.
        """
        logger.debug(f"Checking if there were local changes in {self.local_path}")
        on_disk_hash = self._on_disk_hash()

        return bool(on_disk_hash) and on_disk_hash != hash_directory(
            self.local_path, skiplist=[self.__metadata.FILENAME]
        )

    @abstractmethod
    def _fetch_impl(self, version: Version) -> Version:
        """Fetch the given version of the VCS, should be implemented by the child class."""

    @abstractmethod
    def metadata_revision(self) -> str:
        """Get the revision of the metadata file."""

    @abstractmethod
    def current_revision(self) -> str:
        """Get the revision of the metadata file."""

    @abstractmethod
    def get_diff(self, old_revision: str, new_revision: Optional[str]) -> str:
        """Get the diff of two revisions."""

    @staticmethod
    def is_license_file(filename: str) -> bool:
        """Check if the given filename is a license file."""
        return any(
            fnmatch.fnmatch(filename.lower(), pattern) for pattern in VCS.LICENSE_GLOBS
        )
