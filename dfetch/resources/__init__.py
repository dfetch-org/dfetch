"""Resources needed when dfetch is distributed."""

import importlib.resources as importlib_resources
from contextlib import AbstractContextManager
from pathlib import Path


def _resource_path(filename: str) -> AbstractContextManager[Path]:
    """Get the path to the resource."""
    return importlib_resources.as_file(
        importlib_resources.files(
            "resources" if "__compiled__" in globals() else __name__
        )
        / filename
    )


def template_path() -> AbstractContextManager[Path]:
    """Get path to template."""
    return _resource_path("template.yaml")


TEMPLATE_PATH = _resource_path("template.yaml")
