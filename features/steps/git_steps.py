"""Steps for features tests."""

import os
import pathlib
import subprocess

from behave import given  # pylint: disable=no-name-in-module

from dfetch.util.util import in_directory
from features.steps.generic_steps import generate_file
from features.steps.manifest_steps import generate_manifest


def create_repo():
    subprocess.call(["git", "init", "--initial-branch=master"])
    subprocess.call(["git", "config", "user.email", "you@example.com"])
    subprocess.call(["git", "config", "user.name", "John Doe"])


def commit_all(msg):
    subprocess.call(["git", "add", "-A"])
    subprocess.call(["git", "commit", "-m", f'"{msg}"'])


@given("a git repo with the following submodules")
def step_impl(context):

    create_repo()

    for submodule in context.table:
        subprocess.call(
            ["git", "submodule", "add", submodule["url"], submodule["path"]]
        )

        with in_directory(submodule["path"]):
            subprocess.call(["git", "checkout", submodule["revision"]])
    commit_all("Added submodules")


@given('a git-repository "{name}" with the manifest')
@given('a git repository "{name}"')
def step_impl(context, name):

    remote_path = os.path.join(context.remotes_dir, name)

    pathlib.Path(remote_path).mkdir(parents=True, exist_ok=True)

    with in_directory(remote_path):
        create_repo()

        generate_file("README.md", f"Generated file for {name}")
        if context.text:
            generate_manifest(context)

        commit_all("Initial commit")
        subprocess.call(["git", "tag", "-a", "v1", "-m", "'Some tag'"])
