"""Resources needed when dfetch is distributed."""

import importlib.resources as importlib_resources
from pathlib import Path
from typing import ContextManager

from dfetch import resources  # pylint: disable=import-self


def _resource_path(filename: str) -> ContextManager[Path]:
    """Get the path to the resource."""
    return importlib_resources.as_file(
        importlib_resources.files(
            "resources" if "__compiled__" in globals() else resources
        )
        / filename
    )


def schema_path() -> ContextManager[Path]:
    """Get path to schema."""
    return _resource_path("schema.yaml")


TEMPLATE_PATH = _resource_path("template.yaml")
