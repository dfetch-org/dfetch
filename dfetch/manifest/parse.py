"""Validate manifests using StrictYAML."""

import os
import pathlib
from typing import Any, cast

from strictyaml import StrictYAMLError, YAMLValidationError, load

from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest, ManifestDict
from dfetch.manifest.schema import MANIFEST_SCHEMA
from dfetch.util.util import find_file, prefix_runtime_exceptions

logger = get_logger(__name__)


def _ensure_unique(seq: list[dict[str, Any]], key: str, context: str) -> None:
    """Ensure values for `key` are unique within a sequence of dicts."""
    values = [item.get(key) for item in seq if key in item]
    seen: set[Any] = set()
    dups: set[Any] = set()
    for val in values:
        if val in seen:
            dups.add(val)
        else:
            seen.add(val)

    if dups:
        dup_list = ", ".join(sorted(map(str, dups)))
        raise RuntimeError(
            f"Schema validation failed:\nDuplicate {context}.{key} value(s): {dup_list}"
        )


def parse(path: str) -> Manifest:
    """Parse & validate the given manifest file against the StrictYAML schema.

    Raises:
        RuntimeError: if the file is not valid YAML or violates the schema/uniqueness constraints.
    """
    try:
        manifest_text = pathlib.Path(path).read_text(encoding="UTF-8")
        loaded_manifest = load(manifest_text, schema=MANIFEST_SCHEMA)
    except (YAMLValidationError, StrictYAMLError) as err:
        raise RuntimeError(
            "\n".join(
                [
                    "Schema validation failed:",
                    "",
                    err.context_mark.get_snippet(),
                    "",
                    err.problem,
                ]
            )
        ) from err

    data: dict[str, Any] = cast(dict[str, Any], loaded_manifest.data)
    manifest: ManifestDict = data["manifest"]  # required

    remotes = manifest.get("remotes", [])  # optional
    projects = manifest["projects"]  # required

    _ensure_unique(remotes, "name", "manifest.remotes")  # type: ignore
    _ensure_unique(projects, "name", "manifest.projects")  # type: ignore
    _ensure_unique(projects, "dst", "manifest.projects")  # type: ignore

    return Manifest(manifest, text=manifest_text, path=path)


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


def get_childmanifests(skip: list[str] | None = None) -> list[Manifest]:
    """Parse & validate any manifest file in cwd and return a list of all valid manifests."""
    skip = skip or []
    logger.debug("Looking for sub-manifests")

    childmanifests: list[Manifest] = []
    root_dir = os.getcwd()
    for path in find_file(DEFAULT_MANIFEST_NAME, root_dir):
        path = os.path.realpath(path)

        if os.path.commonprefix((path, root_dir)) != root_dir:
            logger.warning(f"Sub-manifest {path} is outside {root_dir}")
            continue

        if path not in skip:
            logger.debug(f"Found sub-manifests {path}")
            with prefix_runtime_exceptions(
                pathlib.Path(path).relative_to(os.path.dirname(os.getcwd())).as_posix()
            ):
                childmanifests += [parse(path)]

    return childmanifests
