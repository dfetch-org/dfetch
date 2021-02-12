"""Steps for features tests."""

import subprocess

from behave import given  # pylint: disable=no-name-in-module

from dfetch.util.util import in_directory


@given("a git repo with the following submodules")
def step_impl(context):

    subprocess.call(["git", "init"])

    for submodule in context.table:
        subprocess.call(
            ["git", "submodule", "add", submodule["url"], submodule["path"]]
        )

        with in_directory(submodule["path"]):
            subprocess.call(["git", "checkout", submodule["revision"]])
    subprocess.call(["git", "add", "-A"])
    subprocess.call(["git", "commit", "-m", '"Added submodules"'])
