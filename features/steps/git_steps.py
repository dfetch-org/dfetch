"""Steps for features tests."""

import os
import pathlib
import subprocess

from behave import given  # pylint: disable=no-name-in-module

from dfetch.util.util import in_directory
from features.steps.generic_steps import extend_file, generate_file
from features.steps.manifest_steps import generate_manifest


def create_repo():
    subprocess.call(["git", "config", "init.defaultBranch", "master"])
    subprocess.call(["git", "init"])

    subprocess.call(["git", "config", "user.email", "you@example.com"])
    subprocess.call(["git", "config", "user.name", "John Doe"])

    if os.name == "nt":
        # Creates zombie fsmonitor-daemon process that holds files (see https://github.com/git-for-windows/git/issues/3326)
        subprocess.call(
            ["git", "config", "--global", "core.usebuiltinfsmonitor", "false"]
        )


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


@given("a fetched and committed MyProject with the manifest")
def step_impl(context):
    pathlib.Path("MyProject").mkdir(parents=True, exist_ok=True)
    with in_directory("MyProject"):
        create_repo()
        generate_manifest(context)
        context.execute_steps(
            """
            When I run "dfetch update"
            """
        )
        commit_all("Initial commit")


@given('"{path}" in {directory} is changed with')
def step_impl(context, directory, path):
    with in_directory(directory):
        extend_file(path, context.text)


@given('"{path}" in {directory} is changed and committed with')
def step_impl(context, directory, path):
    with in_directory(directory):
        extend_file(path, context.text)
        commit_all("A change")


@given("MyProject with applied patch 'diff.patch'")
def step_impl(context):
    context.execute_steps(
        '''
        Given the manifest 'dfetch.yaml'
            """
            manifest:
                version: '0.0'

                remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

                projects:
                - name: ext/test-repo-tag
                  tag: v2.0
                  dst: ext/test-repo-tag
                  patch: diff.patch
            """
        And the patch file 'diff.patch'
            """
            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,2 +1,2 @@
             # Test-repo
            -A test repo for testing dfetch.
            +A test repo for testing patch.
            """
        When I run "dfetch update"
        '''
    )
