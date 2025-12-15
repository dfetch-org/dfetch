#!/usr/bin/env python3
"""Script to setup a venv."""

import argparse
import pathlib
import subprocess  # nosec
import sys
import venv
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

MIN_VERSION = (3, 9)  # minimum supported; change if needed
RECOMMENDED_VERSION = (3, 13)  # preferred for development


class MyEnvBuilder(venv.EnvBuilder):
    """Create a virtual environment.

    Optionally install extra requirements from pyproject.toml.
    """

    def __init__(
        self,
        *args: Any,
        extra_requirements: str = "",
        **kwargs: Any,
    ) -> None:  # pylint: disable=line-too-long
        """:param extra_requirements: Install any additional parts as mentioned in pyproject.toml."""
        super().__init__(*args, **kwargs)
        self.extra_requirements = (
            f"[{extra_requirements}]" if extra_requirements else ""
        )

    def post_setup(self, context: Any) -> None:
        """Set up proper environment for testing."""
        super().post_setup(context)

        print("Upgrading pip")
        self.pip_install(context, "--upgrade", "pip")
        print("Installing package and any extra requirements")
        self.pip_install(
            context, "--use-pep517", "-e", f"{PROJECT_ROOT!s}{self.extra_requirements}"
        )

    @staticmethod
    def pip_install(context: Any, *args: Any) -> None:
        """Install something using pip.

        We run pip in isolated mode to avoid side effects from
        environment vars, the current directory and anything else
        intended for the global Python environment
        (same as EnvBuilder's _setup_pip)
        """
        subprocess.check_call(  # nosec
            (context.env_exe, "-Im", "pip", "install") + args,
            stderr=subprocess.STDOUT,
        )


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument(
        "-e", "--extra_requirements", type=str, default="development,test,docs"
    )
    ARGS = PARSER.parse_args()

    CURRENT_VERSION = sys.version_info[:2]

    if CURRENT_VERSION < MIN_VERSION:
        raise RuntimeError(
            f"⚠ Unsupported Python version {sys.version_info.major}.{sys.version_info.minor}. "
            f"Please use Python {MIN_VERSION[0]}.{MIN_VERSION[1]} or newer."
        )
    if CURRENT_VERSION != RECOMMENDED_VERSION:
        print(
            f"⚠ Warning: Running with Python {sys.version_info.major}.{sys.version_info.minor}, "
            f"dfetch is primarily developed with Python {RECOMMENDED_VERSION[0]}.{RECOMMENDED_VERSION[1]}."
        )

    MyEnvBuilder(
        clear=False,
        with_pip=True,
        extra_requirements=ARGS.extra_requirements,
    ).create(str(PROJECT_ROOT / "venv"))
