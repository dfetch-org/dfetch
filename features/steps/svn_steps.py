"""Steps for features tests."""

import os
import pathlib
import subprocess

from behave import given  # pylint: disable=no-name-in-module

from dfetch.util.util import in_directory
from features.steps.generic_steps import generate_file, list_dir


def create_svn_server_and_repo(context, name="svn-server"):
    """Create an local svn server and repo and return the path to the repo."""

    server_path = os.path.relpath(context.remotes_dir_path) + "/" + name
    repo_path = "svn-repo"

    pathlib.Path(server_path).mkdir(parents=True, exist_ok=True)
    subprocess.call(["svnadmin", "create", "--fs-type", "fsfs", server_path])

    current_path = "/".join(os.getcwd().split(os.path.sep) + [server_path])
    subprocess.call(["svn", "checkout", f"file:///{current_path}", repo_path])

    return repo_path


def create_stdlayout():
    pathlib.Path("trunk").mkdir(parents=True, exist_ok=True)
    pathlib.Path("branches").mkdir(parents=True, exist_ok=True)
    pathlib.Path("tags").mkdir(parents=True, exist_ok=True)


def add_and_commit(msg):
    subprocess.call(["svn", "add", "--force", "."])
    subprocess.call(["svn", "ci", "-m", f'"{msg}"'])


def commit_all(msg):
    subprocess.call(["svn", "commit", "--depth", "empty", ".", "-m", f'"{msg}"'])


def add_externals(externals):
    """Add the given list of dicts as externals."""
    with open("externals", "w") as external_list:
        for external in externals:
            external_list.write(
                f"{external['url']}@{external['revision']} {external['path']}\n"
            )

    subprocess.call(["svn", "propset", "svn:externals", "-F", external_list.name, "."])
    commit_all("Added externals")
    subprocess.call(["svn", "update"])


@given("a svn repo with the following externals")
def step_impl(context):

    repo_path = create_svn_server_and_repo(context)
    os.chdir(repo_path)
    add_externals(context.table)


@given('a svn-server "{name}" with the files')
def step_impl(context, name):
    repo_path = create_svn_server_and_repo(context, name)

    with in_directory(repo_path):

        create_stdlayout()
        with in_directory("trunk"):
            for file in context.table:
                generate_file(file["path"], "some content")
        add_and_commit("Added files")

@given(u'a non-standard svn-server "{name}" with the files')
def step_impl(context, name):
    repo_path = create_svn_server_and_repo(context, name)

    with in_directory(repo_path):
        for file in context.table:
            generate_file(file["path"], "some content")
        add_and_commit("Added files")

@given(u'a non-standard svn-server "{name}"')
def step_impl(context, name):
    repo_path = create_svn_server_and_repo(context, name)

    with in_directory(repo_path):
        generate_file("SomeFolder/SomeFile.txt", "some content")
        add_and_commit("Added files")
