"""Steps for features tests."""

import os
import subprocess

from behave import given  # pylint: disable=no-name-in-module


def create_svn_server_and_repo():
    """Create an local svn server and repo and return the path to the repo."""

    server_path = "svn-server"
    repo_path = "svn-repo"

    subprocess.call(["svnadmin", "create", "--fs-type", "fsfs", server_path])

    current_path = "/".join(os.getcwd().split(os.path.sep) + [server_path])
    subprocess.call(["svn", "checkout", f"file:///{current_path}", repo_path])

    return repo_path


def add_externals(externals):
    """Add the given list of dicts as externals."""
    with open("externals", "w") as external_list:
        for external in externals:
            external_list.write(
                f"{external['url']}@{external['revision']} {external['path']}\n"
            )

    subprocess.call(["svn", "propset", "svn:externals", "-F", external_list.name, "."])
    subprocess.call(
        ["svn", "commit", "--depth", "empty", ".", "-m", '"Added externals"']
    )
    subprocess.call(["svn", "update"])


@given("a svn repo with the following externals")
def step_impl(context):

    repo_path = create_svn_server_and_repo()
    os.chdir(repo_path)
    add_externals(context.table)
