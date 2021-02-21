"""Test the resources."""
# mypy: ignore-errors
# flake8: noqa

import os

import dfetch.resources


def test_schema_path() -> None:
    """Test that schema path can be used as context manager."""

    with dfetch.resources.schema_path() as schema_path:
        assert os.path.isfile(schema_path)


def test_call_schema_path_twice() -> None:
    """Had a lot of problems with calling contextmanager twice."""

    with dfetch.resources.schema_path() as schema_path:
        assert os.path.isfile(schema_path)

    with dfetch.resources.schema_path() as schema_path:
        assert os.path.isfile(schema_path)
