"""Utilities for finding manifest files."""

import os
import pathlib

from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.util.util import (
    check_no_path_traversal,
    find_file,
    prefix_runtime_exceptions,
)

logger = get_logger(__name__)


def find_manifest() -> str:
    """Find a manifest."""
    paths = find_file(DEFAULT_MANIFEST_NAME, ".")

    if len(paths) == 0:
        raise RuntimeError("No manifests were found!")
    if len(paths) != 1:
        logger.warning(
            f"Multiple manifests found, using {pathlib.Path(paths[0]).as_posix()}"
        )

    return os.path.realpath(paths[0])


def get_submanifests(skip: list[str] | None = None) -> list[Manifest]:
    """Parse & validate any manifest file in cwd and return a list of all valid manifests."""
    skip = skip or []
    logger.debug("Looking for sub-manifests")

    submanifests: list[Manifest] = []
    root_dir = os.getcwd()
    for path in find_file(DEFAULT_MANIFEST_NAME, root_dir):
        path = os.path.realpath(path)

        try:
            check_no_path_traversal(path, root_dir)
        except RuntimeError:
            logger.warning(f"Sub-manifest {path} is outside {root_dir}")
            continue

        if path not in skip:
            logger.debug(f"Found sub-manifest {path}")
            with prefix_runtime_exceptions(
                pathlib.Path(path).relative_to(os.path.dirname(os.getcwd())).as_posix()
            ):
                try:
                    submanifests += [Manifest.from_file(path)]
                except FileNotFoundError:
                    logger.warning(
                        f"Sub-manifest {path} was found but no longer exists"
                    )

    return submanifests
