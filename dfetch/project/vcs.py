"""Version Control system."""

import fnmatch
import os
import pathlib
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence, Tuple

from halo import Halo
from patch_ng import fromfile

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.abstract_check_reporter import AbstractCheckReporter
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
    LICENSE_GLOBS = ["licen[cs]e*", "copying*", "copyright*"]

    def __init__(self, project: ProjectEntry) -> None:
        """Create the VCS."""
        self.__project = project
        self.__metadata = Metadata.from_project_entry(self.__project)

        self._show_animations = not self._running_in_ci()

    @staticmethod
    def _running_in_ci() -> bool:
        """Are we running in CI."""
        ci_env_var = os.getenv("CI", "")
        return bool(ci_env_var) and ci_env_var[0].lower() in ("t", "1", "y")

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
            wanted_branch = self.wanted_version.branch or self.get_default_branch()
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

        with Halo(
            text=f"Fetching {self.__project.name} {to_fetch}",
            spinner="dots",
            text_color="green",
            enabled=self._show_animations,
        ):
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

        if not patch_set:
            raise RuntimeError(f'Invalid patch file: "{self.__project.patch}"')
        if patch_set.apply(0, root=self.local_path, fuzz=True):
            self._log_project(f'Applied patch "{self.__project.patch}"')
        else:
            raise RuntimeError(f'Applying patch "{self.__project.patch}" failed')

    def check_for_update(self, reporters: Sequence[AbstractCheckReporter]) -> None:
        """Check if there is an update available."""
        on_disk_version = self.on_disk_version()
        with Halo(
            text=f"Checking {self.__project.name}",
            spinner="dots",
            text_color="green",
            enabled=self._show_animations,
        ):
            latest_version = self._check_for_newer_version()

        if not latest_version:
            for reporter in reporters:
                reporter.unavailable_project_version(
                    self.__project, self.wanted_version
                )
            return

        if not on_disk_version:
            for reporter in reporters:
                reporter.unfetched_project(
                    self.__project, self.wanted_version, latest_version
                )

            return

        if self._are_there_local_changes():
            for reporter in reporters:
                reporter.local_changes(self.__project)

        self._check_latest_with_on_disk_version(
            latest_version, on_disk_version, reporters
        )

    def _check_latest_with_on_disk_version(
        self,
        latest_version: Version,
        on_disk_version: Version,
        reporters: Sequence[AbstractCheckReporter],
    ) -> None:
        if (latest_version == on_disk_version) or (
            self.revision_is_enough()
            and latest_version.revision
            and latest_version.revision == on_disk_version.revision
        ):
            for reporter in reporters:
                reporter.up_to_date_project(self.__project, latest_version)
        elif on_disk_version == self.wanted_version:
            for reporter in reporters:
                reporter.pinned_but_out_of_date_project(
                    self.__project, self.wanted_version, latest_version
                )
        else:
            for reporter in reporters:
                reporter.out_of_date_project(
                    self.__project, self.wanted_version, on_disk_version, latest_version
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

    @property
    def ignore(self) -> Sequence[str]:
        """Get the files/folders to ignore of this VCS."""
        return self.__project.ignore

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
    def _does_revision_exist(self, revision: str) -> bool:
        """Check if the given revision exists."""

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
        if not os.path.exists(self.__metadata.path):
            return None

        try:
            return Metadata.from_file(self.__metadata.path).version
        except TypeError:
            logger.warning(
                f"{pathlib.Path(self.__metadata.path).relative_to(os.getcwd()).as_posix()}"
                " is an invalid metadata file, not checking on disk version!"
            )
            return None

    def _on_disk_hash(self) -> Optional[str]:
        """Get the hash of the project on disk.

        Returns:
            Str: Could be None if no on disk version
        """
        if not os.path.exists(self.__metadata.path):
            return None

        try:
            return Metadata.from_file(self.__metadata.path).hash
        except TypeError:
            logger.warning(
                f"{pathlib.Path(self.__metadata.path).relative_to(os.getcwd()).as_posix()}"
                " is an invalid metadata file, not checking local hash!"
            )
            return None

    def _check_for_newer_version(self) -> Optional[Version]:
        """Check if a newer version is available on the given branch.

        In case wanted_version does not exist (anymore) on the remote return None.
        """
        if self.wanted_version.tag:
            available_tags = self._list_of_tags()
            if self.wanted_version.tag not in available_tags:
                return None
            return Version(
                tag=latest_tag_from_list(self.wanted_version.tag, available_tags)
            )
        if self.wanted_version.branch == " ":
            branch = ""
        else:
            branch = self.wanted_version.branch or self.get_default_branch()

        if (
            not self.wanted_version.branch
            and self.wanted_version.revision
            and self.revision_is_enough()
        ):
            return (
                Version(revision=self.wanted_version.revision)
                if self._does_revision_exist(self.wanted_version.revision)
                else None
            )

        revision = self._latest_revision_on_branch(branch)
        return Version(revision=revision, branch=branch) if revision else None

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
    def get_diff(self, old_revision: str, new_revision: Optional[str]) -> str:  # noqa
        """Get the diff of two revisions."""

    @abstractmethod
    def get_default_branch(self) -> str:
        """Get the default branch of this repository."""

    @staticmethod
    def is_license_file(filename: str) -> bool:
        """Check if the given filename is a license file."""
        return any(
            fnmatch.fnmatch(filename.lower(), pattern) for pattern in VCS.LICENSE_GLOBS
        )
