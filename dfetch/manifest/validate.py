"""Validate manifests using StrictYAML."""

import pathlib
from collections.abc import Mapping
from typing import Any, cast

from strictyaml import StrictYAMLError, YAMLValidationError, load

from dfetch.manifest.schema import MANIFEST_SCHEMA


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


def validate(path: str) -> None:
    """Validate the given manifest file against the StrictYAML schema.

    Raises:
        RuntimeError: if the file is not valid YAML or violates the schema/uniqueness constraints.
    """
    try:

        loaded_manifest = load(
            pathlib.Path(path).read_text(encoding="UTF-8"), schema=MANIFEST_SCHEMA
        )
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
    manifest: Mapping[str, Any] = data["manifest"]  # required
    projects: list[dict[str, Any]] = manifest["projects"]  # required
    remotes: list[dict[str, Any]] = manifest.get("remotes", []) or []  # optional

    _ensure_unique(remotes, "name", "manifest.remotes")
    _ensure_unique(projects, "name", "manifest.projects")
    _ensure_unique(projects, "dst", "manifest.projects")
