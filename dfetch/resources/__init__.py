"""Resources needed when dfetch is distributed."""

try:
    import importlib.resources as importlib_resources
except ModuleNotFoundError:
    import importlib_resources  # type:ignore

import sys
from pathlib import Path
from typing import ContextManager

from dfetch import resources  # pylint: disable=import-self


def _resource_path(filename: str) -> ContextManager[Path]:
    """Get the path to the resource."""
    if sys.version_info >= (3, 9):
        return importlib_resources.as_file(
            importlib_resources.files(resources) / filename
        )
    return importlib_resources.path(  # pylint: disable=deprecated-method
        resources, filename
    )


def schema_path() -> ContextManager[Path]:
    """Get path to schema."""
    return _resource_path("schema.yaml")


TEMPLATE_PATH = _resource_path("template.yaml")
