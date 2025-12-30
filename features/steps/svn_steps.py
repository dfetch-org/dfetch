"""Steps for features tests."""

# pylint: disable=function-redefined, missing-function-docstring, import-error, not-callable
# pyright: reportRedeclaration=false, reportAttributeAccessIssue=false, reportCallIssue=false

import os
import pathlib
import subprocess

from behave import given  # pylint: disable=no-name-in-module

from dfetch.util.util import in_directory
from features.steps.generic_steps import call_command, extend_file, generate_file
from features.steps.manifest_steps import generate_manifest


def create_svn_server_and_repo(context, name="svn-server"):
    """Create an local svn server and repo and return the path to the repo."""

    server_path = os.path.relpath(context.remotes_dir_path) + "/" + name
    repo_path = name

    pathlib.Path(server_path).mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["svnadmin", "create", "--fs-type", "fsfs", server_path])

    current_path = "/".join(os.getcwd().split(os.path.sep) + [server_path])
    subprocess.check_call(["svn", "checkout", f"file:///{current_path}", repo_path])

    return repo_path


def create_stdlayout():
    pathlib.Path("trunk").mkdir(parents=True, exist_ok=True)
    pathlib.Path("branches").mkdir(parents=True, exist_ok=True)
    pathlib.Path("tags").mkdir(parents=True, exist_ok=True)


def add_and_commit(msg):
    subprocess.check_call(["svn", "update", "."])
    subprocess.check_call(["svn", "add", "--force", "."])
    subprocess.check_call(["svn", "ci", "-m", f'"{msg}"'])


def commit_all(msg):
    subprocess.check_call(["svn", "update", "."])
    subprocess.check_call(["svn", "commit", "--depth", "empty", ".", "-m", f'"{msg}"'])


def create_tag(tag_name):
    """Create a tag from trunk."""
    subprocess.check_call(["svn", "copy", "trunk", f"tags/{tag_name}"])
    subprocess.check_call(["svn", "ci", "-m", f'"Created tag {tag_name}"'])


def add_externals(externals):
    """Add the given list of dicts as externals."""
    with open("externals", "w", encoding="UTF-8") as external_list:
        for external in externals:
            revision = f"@{external['revision']}" if external["revision"] else ""
            external_list.write(f"{external['url']}{revision} {external['path']}\n")

    subprocess.check_call(
        ["svn", "propset", "svn:externals", "-F", external_list.name, "."]
    )
    commit_all("Added externals")


@given("a svn repo with the following externals")
def step_impl(context):
    repo_path = create_svn_server_and_repo(context)
    os.chdir(repo_path)
    add_externals(context.table)


@given('a svn-server "{name}"')
@given('a svn-server "{name}" with the files')
@given('a svn-server "{name}" with the tag "{tag_name}"')
def step_impl(context, name, tag_name=None):
    repo_path = create_svn_server_and_repo(context, name)

    files = context.table or [{"path": "README.md"}]

    with in_directory(repo_path):
        create_stdlayout()
        with in_directory("trunk"):
            for file in files:
                generate_file(file["path"], "some content")
        add_and_commit("Added files")
        if tag_name:
            create_tag(tag_name)


@given('a new tag "{tag_name}" is added to "{name}"')
def step_impl(_, tag_name, name):
    with in_directory(name):
        create_tag(tag_name)


@given('a non-standard svn-server "{name}" with the files')
def step_impl(context, name):
    repo_path = create_svn_server_and_repo(context, name)

    with in_directory(repo_path):
        for file in context.table:
            generate_file(file["path"], "some content")
        add_and_commit("Added files")


@given('a non-standard svn-server "{name}"')
def step_impl(context, name):
    repo_path = create_svn_server_and_repo(context, name)

    with in_directory(repo_path):
        generate_file("SomeFolder/SomeFile.txt", "some content")
        add_and_commit("Added files")


@given("a fetched and committed MySvnProject with the manifest")
def step_impl(context):
    repo_path = create_svn_server_and_repo(context, "MySvnProject")

    with in_directory(repo_path):
        generate_manifest(context)
        call_command(context, ["update"])
        add_and_commit("Initial commit")


@given('"{path}" in {directory} is changed, added and committed with')
def step_impl(context, directory, path):
    with in_directory(directory):
        extend_file(path, context.text)
        add_and_commit(f"Added {path} to {directory}")


@given("files as '{pattern}' are ignored in '{directory}' in svn")
def step_impl(_, pattern, directory):
    with in_directory(directory):
        subprocess.check_call(["svn", "propset", "svn:ignore", pattern, "."])
        commit_all(f"Ignore {pattern} files")
