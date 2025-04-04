"""Steps for features tests."""

# pyright: reportRedeclaration=false, reportAttributeAccessIssue=false
# pylint: disable=function-redefined, missing-function-docstring

import difflib
import json
import os
import pathlib
import re
from itertools import zip_longest
from typing import Iterable, List, Optional, Pattern, Tuple

from behave import given, then, when  # pylint: disable=no-name-in-module

from dfetch.__main__ import DfetchFatalException, run
from dfetch.util.util import in_directory

ansi_escape = re.compile(r"\x1b(?:[@A-Z\\-_]|\[[0-9:;<=>?]*[ -/]*[@-~])")
dfetch_title = re.compile(r"Dfetch \(\d+.\d+.\d+\)")
timestamp = re.compile(r"\d+\/\d+\/\d+, \d+:\d+:\d+")
git_hash = re.compile(r"(\s?)[a-f0-9]{40}(\s?)")
iso_timestamp = re.compile(r'"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{6}\+\d{2}:\d{2}')
urn_uuid = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def remote_server_path(context):
    """Get the path to the remote dir."""
    return "/".join(context.remotes_dir_path.split(os.sep))


def call_command(context, args: list[str], path: Optional[str] = ".") -> None:
    context.log_capture.buffer = []
    with in_directory(path or "."):
        try:
            run(args)
            context.cmd_returncode = 0
        except DfetchFatalException:
            context.cmd_returncode = 1
    # Remove the color code + title
    context.cmd_output = dfetch_title.sub(
        "", ansi_escape.sub("", context.log_capture.getvalue())
    )


def check_file(path, content):
    """Check a file."""
    with open(path, "r", encoding="UTF-8") as file_to_check:
        check_content(content.splitlines(True), file_to_check.readlines())


def check_file_exists(path):
    """Check a file."""
    assert os.path.isfile(path), f"Expected {path} to exist, but it didn't!"


def check_json(path, content):
    """Check a file."""

    with open(path, "r", encoding="UTF-8") as file_to_check:
        actual_json = json.load(file_to_check)
    expected_json = json.loads(content)

    if "bomFormat" in expected_json:
        sort_sbom(expected_json)
    if "bomFormat" in actual_json:
        sort_sbom(actual_json)

    check_content(
        json.dumps(expected_json, indent=4, sort_keys=True).splitlines(),
        json.dumps(actual_json, indent=4, sort_keys=True).splitlines(),
    )


def sort_sbom(sbom):
    """Sort some fields in an sbom."""

    for tool in sbom["metadata"]["tools"]:
        if "externalReferences" in tool:
            tool["externalReferences"] = sorted(
                tool["externalReferences"], key=lambda x: x["type"]
            )

    sbom["metadata"]["tools"] = sorted(
        sbom["metadata"]["tools"], key=lambda x: x["name"]
    )


def check_content(
    expected_content: Iterable[str], actual_content: Iterable[str]
) -> None:
    """Compare two texts as list of strings."""

    for line_nr, (actual, expected) in enumerate(
        zip_longest(actual_content, expected_content, fillvalue=""), start=1
    ):
        expected = multisub(
            patterns=[
                (git_hash, r"\1[commit hash]\2"),
                (iso_timestamp, "[timestamp]"),
                (urn_uuid, "[urn-uuid]"),
            ],
            text=expected,
        )

        actual = multisub(
            patterns=[
                (git_hash, r"\1[commit hash]\2"),
                (iso_timestamp, "[timestamp]"),
                (urn_uuid, "[urn-uuid]"),
            ],
            text=actual,
        )

        assert (
            actual.strip() == expected.strip()
        ), f"Line {line_nr}: Actual >>{actual.strip()}<< != Expected >>{expected.strip()}<<"


def generate_file(path, content):
    opt_dir = path.rsplit("/", maxsplit=1)

    if len(opt_dir) > 1:
        pathlib.Path(opt_dir[0]).mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="UTF-8") as new_file:
        for line in content.splitlines():
            print(line, file=new_file)


def extend_file(path, content):
    with open(path, "a", encoding="UTF-8") as existing_file:
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


@given("the patch file '{name}'")
def step_impl(context, name):
    generate_file(os.path.join(os.getcwd(), name), context.text)


@given('the metadata file "{metadata_file}" of "{project_path}" is corrupt')
def step_impl(_, metadata_file, project_path):
    generate_file(
        os.path.join(os.getcwd(), project_path, metadata_file), "Corrupt metadata!"
    )


@given("all projects are updated in {path}")
@given("all projects are updated")
def step_impl(context, path=None):
    if path:
        context.execute_steps(f'When I run "dfetch update" in {path}')
    else:
        context.execute_steps('When I run "dfetch update"')
    assert not context.cmd_returncode, context.cmd_output


@when('I run "dfetch {args}" in {path}')
@when('I run "dfetch {args}"')
def step_impl(context, args, path=None):
    """Call a command."""
    call_command(context, args.split(), path)


@when('"{path}" in {directory} is changed locally')
def step_impl(_, directory, path):
    with in_directory(directory):
        extend_file(path, "Some text")


@then("the patched '{name}' is")
def step_impl(context, name):
    """Check a manifest."""
    check_file(name, context.text)


@then("the first line of '{name}' is changed to")
def step_impl(context, name):
    """Check the first line of the file."""
    with open(name, "r", encoding="UTF-8") as file_to_check:
        check_content(context.text.strip(), file_to_check.readline().strip())


@then("the patch file '{name}' is generated")
def step_impl(_, name):
    """Check a manifest."""
    check_file_exists(name)


@then("the '{name}' file contains")
def step_impl(context, name):
    if name.endswith(".json"):
        check_json(name, context.text)
    else:
        check_file(name, context.text)


def multisub(patterns: List[Tuple[Pattern[str], str]], text: str) -> str:
    """Apply a list of tuples that each contain a regex + replace string."""
    for pattern, replace in patterns:
        text = pattern.sub(replace, text)

    return text


@then("the output shows")
def step_impl(context):
    expected_text = multisub(
        patterns=[
            (git_hash, r"\1[commit hash]\2"),
            (timestamp, "[timestamp]"),
            (dfetch_title, ""),
        ],
        text=context.text,
    )

    actual_text = multisub(
        patterns=[
            (git_hash, r"\1[commit hash]\2"),
            (timestamp, "[timestamp]"),
            (ansi_escape, ""),
            (
                re.compile(f"file:///{remote_server_path(context)}"),
                "some-remote-server",
            ),
        ],
        text=context.cmd_output,
    )

    diff = difflib.ndiff(actual_text.splitlines(), expected_text.splitlines())

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
