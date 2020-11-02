#!python3.7
"""Script to setup a venv."""

import argparse
import subprocess
import venv

from typing import Any


class MyEnvBuilder(venv.EnvBuilder):
    """Create a virtual environment.

    Conditions for use:
     + A `requirements.txt` file must exist
     By default this is relative to the current run path, but this can be specified programmatically.
    """

    def __init__(
        self, *args: Any, requirements: str = "", **kwargs: Any
    ) -> None:  # pylint: disable=line-too-long
        """:param requirements: Can be any path. If non, this step is skipped."""
        super().__init__(*args, **kwargs)
        self.requirements = requirements or ["requirements.txt"]

    def post_setup(self, context: Any) -> None:
        """Set up proper environment for testing."""
        super().post_setup(context)

        print("Upgrading pip")
        self.pip_install(context, "--upgrade", "pip")
        for reqs in self.requirements:
            print("Installing requirements from {}".format(reqs))
            self.pip_install(context, "-r", reqs)
        print("Installing package")
        self.pip_install(context, "-e", ".")

    @staticmethod
    def pip_install(context: Any, *args: Any) -> None:
        """Install something using pip.

        We run pip in isolated mode to avoid side effects from
        environment vars, the current directory and anything else
        intended for the global Python environment
        (same as EnvBuilder's _setup_pip)
        """
        ret = subprocess.call(
            (context.env_exe, "-Im", "pip", "install") + args,
            stderr=subprocess.STDOUT,  # nosec
        )
        if ret:
            raise Exception("pip install command result was not 0 but %d" % ret)


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("-r", "--requirements", type=str, nargs="*")
    ARGS = PARSER.parse_args()

    MyEnvBuilder(clear=True, with_pip=True, requirements=ARGS.requirements).create(
        "venv"
    )
