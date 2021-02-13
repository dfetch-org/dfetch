"""Steps for features tests."""

import difflib
import os
import re
import subprocess

from behave import given, then, when  # pylint: disable=no-name-in-module

ansi_escape = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
dfetch_title = re.compile(r"Dfetch \(\d+.\d+.\d+\)")


@given("all projects are updated")
def step_impl(context):
    context.execute_steps('When I run "dfetch update"')


@when('I run "{cmd}"')
def step_impl(context, cmd):
    """Call a command."""
    context.cmd_output = dfetch_title.sub(
        "", subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT, text=True)
    )


@then("the output shows")
def step_impl(context):
    expected_text = dfetch_title.sub("", context.text).splitlines()
    actual_text = ansi_escape.sub("", context.cmd_output)

    diff = difflib.ndiff(actual_text.splitlines(), expected_text)

    diffs = [x for x in diff if x[0] in ("+", "-")]
    if diffs:
        comp = "\n".join(diffs)
        print(actual_text)
        print(comp)
        assert False, "Output not as expected!"


@then("the following projects are fetched")
def step_impl(context):

    for project in context.table:
        assert os.path.exists(project["path"]), f"No project found at {project}"
        assert os.listdir(project["path"]), f"{project} is just an empty directory!"
