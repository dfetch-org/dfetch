"""Resources needed when dfetch is distributed."""

try:
    import importlib.resources as importlib_resources
except ModuleNotFoundError:
    import importlib_resources  # type:ignore

from pathlib import Path
from typing import ContextManager

from dfetch import resources  # pylint: disable=import-self


def schema_path() -> ContextManager[Path]:
    """Get path to schema."""
    return importlib_resources.path(resources, "schema.yaml")


TEMPLATE_PATH = importlib_resources.path(resources, "template.yaml")
