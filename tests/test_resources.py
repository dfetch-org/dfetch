"""Test the resources."""

# mypy: ignore-errors
# flake8: noqa

import os

import dfetch.resources


def test_template_path() -> None:
    """Test that template path can be used as context manager."""

    with dfetch.resources.template_path() as template_path:
        assert os.path.isfile(template_path)


def test_call_template_path_twice() -> None:
    """Had a lot of problems with calling contextmanager twice."""

    with dfetch.resources.template_path() as template_path:
        assert os.path.isfile(template_path)

    with dfetch.resources.template_path() as template_path:
        assert os.path.isfile(template_path)
