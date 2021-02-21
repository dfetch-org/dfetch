"""Resources needed when dfetch is distributed."""

import importlib.resources
from pathlib import Path
from typing import ContextManager

from dfetch import resources  # pylint: disable=import-self


def schema_path() -> ContextManager[Path]:
    """Get path to schema."""
    return importlib.resources.path(resources, "schema.yaml")


TEMPLATE_PATH = importlib.resources.path(resources, "template.yaml")
