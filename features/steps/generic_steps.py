"""Steps for features tests."""

import difflib
import os
import pathlib
import re
import subprocess

from behave import given, then, when  # pylint: disable=no-name-in-module

from dfetch.util.util import in_directory

ansi_escape = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
dfetch_title = re.compile(r"Dfetch \(\d+.\d+.\d+\)")


def generate_file(path, content):

    opt_dir = path.rsplit("/", maxsplit=1)

    if len(opt_dir) > 1:
        pathlib.Path(opt_dir[0]).mkdir(parents=True, exist_ok=True)

    with open(path, "w") as new_file:
        for line in content.splitlines():
            print(line, file=new_file)


def extend_file(path, content):

    with open(path, "a") as existing_file:
        for line in content.splitlines():
            print(line, file=existing_file)


def list_dir(path):

    # Get list of all nodes
    nodes = [os.path.normpath(path).split(os.sep)]
    for root, dirs, files in os.walk(path, followlinks=False):
        root = os.path.relpath(root)
        for name in dirs:
            nodes += [os.path.normpath(os.path.join(root, name)).split(os.sep)]
        for name in files:
            nodes += [os.path.normpath(os.path.join(root, name)).split(os.sep)]

    result = ""
    prev_node = []
    for node in list(sorted(nodes)) + [""]:
        if prev_node:
            end = ""
            if "".join(node).startswith("".join(prev_node)):
                end = "/"
            result += "    " * (len(prev_node) - 1) + prev_node[-1] + end + os.linesep
        prev_node = node

    return result


@given("all projects are updated in {path}")
@given("all projects are updated")
def step_impl(context, path=None):

    if path:
        context.execute_steps(f'When I run "dfetch update" in {path}')
    else:
        context.execute_steps('When I run "dfetch update"')
    assert not context.cmd_returncode, context.cmd_output


@when('I run "{cmd}" in {path}')
@when('I run "{cmd}"')
def step_impl(context, cmd, path=None):
    """Call a command."""
    try:
        context.cmd_output = dfetch_title.sub(
            "",
            subprocess.check_output(
                cmd.split(), stderr=subprocess.STDOUT, text=True, cwd=path
            ),
        )
        context.cmd_returncode = 0
    except subprocess.CalledProcessError as exc:
        context.cmd_output = dfetch_title.sub("", exc.stdout)
        context.cmd_returncode = exc.returncode


@when('"{path}" in {directory} is changed locally')
def step_impl(context, directory, path):

    with in_directory(directory):
        extend_file(path, "Some text")


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


@then("'{path}' looks like")
def step_impl(context, path):
    expected_dir = context.text.strip()
    actual_dir = list_dir(path).strip()

    assert expected_dir == actual_dir, os.linesep.join(
        ["", "Expected:", expected_dir, "", "Actual:", actual_dir]
    )
