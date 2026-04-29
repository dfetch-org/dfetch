"""SubProject — the domain aggregate for a vendored dependency."""

import os
import pathlib
from collections.abc import Callable, Sequence

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.abstract_check_reporter import AbstractCheckReporter
from dfetch.project.fetcher import Fetcher, VcsFetcher
from dfetch.project.metadata import InvalidMetadataError, Metadata
from dfetch.util.util import hash_directory, safe_rm
from dfetch.vcs.patch import Patch

logger = get_logger(__name__)


class SubProject:
    """A vendored dependency declared in the manifest.

    Orchestrates the update lifecycle (fetch, patch, metadata persistence)
    and delegates all VCS- or archive-specific behaviour to a :class:`Fetcher`.
    """

    def __init__(self, project: ProjectEntry, fetcher: Fetcher) -> None:
        """Create a SubProject backed by *fetcher*."""
        self.__project = project
        self.__fetcher = fetcher
        self.__metadata = Metadata.from_project_entry(project)
        self._show_animations = not self._running_in_ci()

    # ------------------------------------------------------------------
    # VCS dispatch
    # ------------------------------------------------------------------

    def as_vcs(self) -> VcsFetcher | None:
        """Return the fetcher cast to VcsFetcher, or None for archive."""
        return self.__fetcher if isinstance(self.__fetcher, VcsFetcher) else None

    # ------------------------------------------------------------------
    # Thin delegates exposed to command layer
    # ------------------------------------------------------------------

    def list_of_branches(self) -> list[str]:
        """Return all branches, or an empty list for archive dependencies."""
        vcs = self.as_vcs()
        return vcs.list_of_branches() if vcs else []

    def list_of_tags(self) -> list[str]:
        """Return all tags, or an empty list for archive dependencies."""
        vcs = self.as_vcs()
        return vcs.list_of_tags() if vcs else []

    def get_default_branch(self) -> str:
        """Return the default branch, or an empty string for archive dependencies."""
        vcs = self.as_vcs()
        return vcs.get_default_branch() if vcs else ""

    # ------------------------------------------------------------------
    # Core properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Project name."""
        return self.__project.name

    @property
    def local_path(self) -> str:
        """Local destination path."""
        return self.__project.destination

    @property
    def wanted_version(self) -> Version:
        """Desired version as expressed in the manifest."""
        return self.__fetcher.wanted_version(self.__project)

    @property
    def metadata_path(self) -> str:
        """Path to the on-disk metadata file."""
        return self.__metadata.path

    @property
    def remote(self) -> str:
        """Remote URL."""
        return self.__metadata.remote_url

    @property
    def source(self) -> str:
        """Source sub-path within the remote."""
        return self.__project.source

    @property
    def ignore(self) -> Sequence[str]:
        """Files/folders to exclude after fetch."""
        return self.__project.ignore

    @property
    def patch(self) -> Sequence[str]:
        """Patch files to apply after fetch."""
        return self.__project.patch

    # ------------------------------------------------------------------
    # Version resolution
    # ------------------------------------------------------------------

    def check_wanted_with_local(self) -> tuple[Version | None, Version | None]:
        """Return (wanted, have) version pair for the current manifest entry.

        For archive dependencies, identity is the revision field (URL or hash).
        For VCS dependencies, branch and revision semantics apply.
        """
        on_disk = self.on_disk_version()
        if not on_disk:
            return (self.wanted_version, None)
        vcs = self.as_vcs()
        if vcs is not None:
            return self._resolve_vcs_versions(vcs, on_disk)
        return (
            Version(revision=self.wanted_version.revision),
            Version(revision=on_disk.revision),
        )

    def _resolve_vcs_versions(
        self, vcs: VcsFetcher, on_disk: Version
    ) -> tuple[Version, Version]:
        """Return (wanted, have) using VCS branch/revision semantics."""
        if self.wanted_version.tag:
            return (
                Version(tag=self.wanted_version.tag),
                Version(tag=on_disk.tag),
            )
        wanted_branch, on_disk_branch = "", ""
        if not (self.wanted_version.revision and vcs.revision_is_enough()):
            wanted_branch = self.wanted_version.branch or vcs.get_default_branch()
            on_disk_branch = on_disk.branch
        wanted_revision = (
            self.wanted_version.revision
            or vcs.latest_revision_on_branch(wanted_branch)
        )
        return (
            Version(revision=wanted_revision, branch=wanted_branch),
            Version(revision=on_disk.revision, branch=on_disk_branch),
        )

    def update_is_required(self, force: bool = False) -> Version | None:
        """Return the version to fetch, or None when already up-to-date."""
        wanted, current = self.check_wanted_with_local()
        if not force and wanted == current:
            self._log_project(f"up-to-date ({current})")
            return None
        logger.debug(f"{self.__project.name} Current ({current}), Available ({wanted})")
        return wanted

    # ------------------------------------------------------------------
    # Update lifecycle
    # ------------------------------------------------------------------

    def update(
        self,
        force: bool = False,
        ignored_files_callback: Callable[[], Sequence[str]] | None = None,
        patch_count: int = -1,
    ) -> None:
        """Fetch and install this subproject if an update is required.

        Args:
            force: Ignore version match and local-change checks.
            ignored_files_callback: Called before and after fetch to obtain
                files that should not contribute to the stored hash.
            patch_count: Number of patches to apply (-1 means all).
        """
        to_fetch = self.update_is_required(force)
        if not to_fetch:
            return

        pre_fetch_ignored = self._collect_ignored(ignored_files_callback)

        if not force and self._are_there_local_changes(pre_fetch_ignored):
            self._log_project(
                "skipped - local changes after last update (use --force to overwrite)"
            )
            return

        if os.path.exists(self.local_path):
            logger.debug(f"Clearing destination {self.local_path}")
            safe_rm(self.local_path)

        with logger.status(
            self.__project.name,
            f"Fetching {to_fetch}",
            enabled=self._show_animations,
        ):
            actually_fetched, dependency = self.__fetcher.fetch(
                to_fetch,
                self.local_path,
                self.__project.name,
                self.source,
                self.ignore,
            )
        self._log_project(f"Fetched {actually_fetched}")

        applied_patches = self._apply_patches(patch_count)

        post_fetch_ignored = self._collect_ignored(ignored_files_callback)

        self.__metadata.fetched(
            actually_fetched,
            hash_=hash_directory(
                self.local_path,
                skiplist=[self.__metadata.FILENAME] + post_fetch_ignored,
            ),
            patch_=applied_patches,
            dependencies=list(dependency),
        )

        logger.debug(f"Writing repo metadata to: {self.__metadata.path}")
        self.__metadata.dump()

    def _collect_ignored(
        self, callback: Callable[[], Sequence[str]] | None
    ) -> list[str]:
        return list(callback()) if callback else []

    def _apply_patches(self, count: int = -1) -> list[str]:
        """Apply manifest patches; return list of applied patch paths."""
        cwd = pathlib.Path(".").resolve()
        applied_patches = []
        count = len(self.__project.patch) if count == -1 else count
        for patch in self.__project.patch[:count]:
            patch_path = (cwd / patch).resolve()
            try:
                relative_patch_path = patch_path.relative_to(cwd)
            except ValueError:
                self._log_project(f'Skipping patch "{patch}" which is outside {cwd}.')
                continue
            if not patch_path.exists():
                self._log_project(f"Skipping non-existent patch {patch}")
                continue
            normalized = str(relative_patch_path.as_posix())
            self._log_project(f'Applying patch "{normalized}"')
            result = Patch.from_file(normalized).apply(root=self.local_path)
            if result.encoding_warning:
                self._log_project(
                    f'After retrying found that patch-file "{normalized}" '
                    "is not UTF-8 encoded, consider saving it with UTF-8 encoding."
                )
            applied_patches.append(normalized)
        return applied_patches

    # ------------------------------------------------------------------
    # Check for updates
    # ------------------------------------------------------------------

    def check_for_update(
        self, reporters: Sequence[AbstractCheckReporter], files_to_ignore: Sequence[str]
    ) -> None:
        """Check whether a newer version is available and report via *reporters*."""
        on_disk_version = self.on_disk_version()
        with logger.status(
            self.__project.name, "Checking", enabled=self._show_animations
        ):
            latest_version = self.__fetcher.latest_available_version(self.wanted_version)

        if not latest_version:
            self._report_unavailable_version(reporters)
            return

        if not on_disk_version:
            self._report_unfetched_project(reporters, latest_version)
            return

        if self._are_there_local_changes(files_to_ignore):
            self._report_local_changes(reporters)

        self._check_latest_with_on_disk_version(latest_version, on_disk_version, reporters)

    def _versions_match(self, latest: Version, on_disk: Version) -> bool:
        vcs = self.as_vcs()
        if vcs is not None:
            return (latest == on_disk) or (
                vcs.revision_is_enough()
                and bool(latest.revision)
                and latest.revision == on_disk.revision
            )
        return latest == on_disk

    def _select_check_action(
        self, latest_version: Version, on_disk_version: Version
    ) -> Callable[[AbstractCheckReporter], None]:
        if self._versions_match(latest_version, on_disk_version):
            return lambda r: r.up_to_date_project(self.__project, latest_version)
        if on_disk_version == self.wanted_version:
            return lambda r: r.pinned_but_out_of_date_project(
                self.__project, self.wanted_version, latest_version
            )
        return lambda r: r.out_of_date_project(
            self.__project, self.wanted_version, on_disk_version, latest_version
        )

    def _check_latest_with_on_disk_version(
        self,
        latest_version: Version,
        on_disk_version: Version,
        reporters: Sequence[AbstractCheckReporter],
    ) -> None:
        report = self._select_check_action(latest_version, on_disk_version)
        for reporter in reporters:
            report(reporter)

    # ------------------------------------------------------------------
    # Freeze
    # ------------------------------------------------------------------

    def freeze_project(self, project: ProjectEntry) -> str | None:
        """Pin *project* to its current on-disk version via the fetcher."""
        return self.__fetcher.freeze(project, self.on_disk_version())

    # ------------------------------------------------------------------
    # On-disk state
    # ------------------------------------------------------------------

    def on_disk_version(self) -> Version | None:
        """Read the on-disk version from metadata; return None if absent or invalid."""
        if not os.path.exists(self.__metadata.path):
            return None
        try:
            return Metadata.from_file(self.__metadata.path).version
        except InvalidMetadataError:
            logger.print_warning_line(
                self.__project.name,
                f"{pathlib.Path(self.__metadata.path).relative_to(os.getcwd()).as_posix()}"
                " is an invalid metadata file, not checking on disk version!",
            )
            return None

    def _on_disk_hash(self) -> str | None:
        """Read the stored directory hash; return None if absent or invalid."""
        if not os.path.exists(self.__metadata.path):
            return None
        try:
            return Metadata.from_file(self.__metadata.path).hash
        except InvalidMetadataError:
            logger.print_warning_line(
                self.__project.name,
                f"{pathlib.Path(self.__metadata.path).relative_to(os.getcwd()).as_posix()}"
                " is an invalid metadata file, not checking local hash!",
            )
            return None

    def _are_there_local_changes(self, files_to_ignore: Sequence[str]) -> bool:
        logger.debug(f"Checking if there were local changes in {self.local_path}")
        on_disk_hash = self._on_disk_hash()
        return bool(on_disk_hash) and on_disk_hash != hash_directory(
            self.local_path,
            skiplist=[self.__metadata.FILENAME] + list(files_to_ignore),
        )

    # ------------------------------------------------------------------
    # Reporters
    # ------------------------------------------------------------------

    def _report_unavailable_version(
        self, reporters: Sequence[AbstractCheckReporter]
    ) -> None:
        for reporter in reporters:
            reporter.unavailable_project_version(self.__project, self.wanted_version)

    def _report_unfetched_project(
        self, reporters: Sequence[AbstractCheckReporter], latest_version: Version
    ) -> None:
        for reporter in reporters:
            reporter.unfetched_project(self.__project, self.wanted_version, latest_version)

    def _report_local_changes(self, reporters: Sequence[AbstractCheckReporter]) -> None:
        for reporter in reporters:
            reporter.local_changes(self.__project)

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log_project(self, msg: str) -> None:
        logger.print_info_line(self.__project.name, msg)

    @staticmethod
    def _log_tool(name: str, msg: str) -> None:
        logger.print_report_line(name, msg.strip())

    @staticmethod
    def _running_in_ci() -> bool:
        ci_env_var = os.getenv("CI", "")
        return bool(ci_env_var) and ci_env_var[0].lower() in ("t", "1", "y")
