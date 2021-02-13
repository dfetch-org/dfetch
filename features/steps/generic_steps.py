"""Steps for features tests."""

import os
import subprocess

from behave import then, when  # pylint: disable=no-name-in-module


@when('I run "{cmd}"')
def step_impl(context, cmd):
    """Call a command."""
    assert subprocess.call(cmd.split()) == 0


@then("the following projects are fetched")
def step_impl(context):

    for project in context.table:
        assert os.path.exists(project["path"]), f"No project found at {project}"
        assert os.listdir(project["path"]), f"{project} is just an empty directory!"
