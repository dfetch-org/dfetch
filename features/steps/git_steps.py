"""Steps for features tests."""

import os
import pathlib
import subprocess

from behave import given  # pylint: disable=no-name-in-module

from dfetch.util.util import in_directory
from features.steps.generic_steps import extend_file, generate_file
from features.steps.manifest_steps import generate_manifest


def create_repo():
    subprocess.call(["git", "init", "--initial-branch=master"])
    subprocess.call(["git", "config", "user.email", "you@example.com"])
    subprocess.call(["git", "config", "user.name", "John Doe"])


def commit_all(msg):
    subprocess.call(["git", "add", "-A"])
    subprocess.call(["git", "commit", "-m", f'"{msg}"'])


def tag(name: str):
    subprocess.call(["git", "tag", "-a", name, "-m", f"'Some tag'"])


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


@given('a new tag "{tagname}" is added to git-repository "{name}"')
def step_impl(context, tagname, name):
    remote_path = os.path.join(context.remotes_dir, name)
    with in_directory(remote_path):
        extend_file("README.md", f"New line for creating {tagname}")
        commit_all("Extend readme")
        tag(tagname)


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
        tag("v1")


@given('a git-repository "{name}" with the files')
def step_impl(context, name):
    remote_path = os.path.join(context.remotes_dir, name)
    pathlib.Path(remote_path).mkdir(parents=True, exist_ok=True)

    with in_directory(remote_path):
        create_repo()

        for file in context.table:
            generate_file(file["path"], "some content")

        commit_all("Initial commit")
        tag("v1")


@given('MyProject with dependency "SomeProject.git" that must be updated')
def step_impl(context):
    context.execute_steps(
        '''
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProject
                      url: some-remote-server/SomeProject.git
                      tag: v1
            """
        And a git repository "SomeProject.git"
        And all projects are updated in MyProject
        And a new tag "v2" is added to git-repository "SomeProject.git"
        When the manifest 'dfetch.yaml' in MyProject is changed to
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProject
                      url: some-remote-server/SomeProject.git
                      tag: v2
            """
        '''
    )
