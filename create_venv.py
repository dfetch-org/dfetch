#!python3.7
"""Script to setup a venv."""

import argparse
import subprocess  # nosec
import venv
from typing import Any, Optional


class MyEnvBuilder(venv.EnvBuilder):
    """Create a virtual environment.

    Conditions for use:
     + A `requirements.txt` file must exist
     By default this is relative to the current run path, but this can be specified programmatically.
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
        self.pip_install(context, "--use-pep517", "-e", f".{self.extra_requirements}")

    @staticmethod
    def pip_install(context: Any, *args: Any) -> None:
        """Install something using pip.

        We run pip in isolated mode to avoid side effects from
        environment vars, the current directory and anything else
        intended for the global Python environment
        (same as EnvBuilder's _setup_pip)
        """
        ret = subprocess.call(  # nosec
            (context.env_exe, "-Im", "pip", "install") + args,
            stderr=subprocess.STDOUT,
        )
        if ret:
            raise Exception("pip install command result was not 0 but %d" % ret)


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("-e", "--extra_requirements", type=str)
    ARGS = PARSER.parse_args()

    MyEnvBuilder(
        clear=False,
        with_pip=True,
        extra_requirements=ARGS.extra_requirements,
    ).create("venv")
