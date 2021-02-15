"""Steps for features tests."""

import os
import pathlib
import subprocess

from behave import given  # pylint: disable=no-name-in-module

from dfetch.util.util import in_directory
from features.steps.generic_steps import generate_file
from features.steps.manifest_steps import generate_manifest


@given("a git repo with the following submodules")
def step_impl(context):

    subprocess.call(["git", "init"])

    for submodule in context.table:
        subprocess.call(
            ["git", "submodule", "add", submodule["url"], submodule["path"]]
        )

        with in_directory(submodule["path"]):
            subprocess.call(["git", "checkout", submodule["revision"]])
    subprocess.call(["git", "add", "-A"])
    subprocess.call(["git", "commit", "-m", '"Added submodules"'])


@given('a git-repository "{name}" with the manifest')
@given('a git repository "{name}"')
def step_impl(context, name):

    remote_path = os.path.join(context.remotes_dir, name)

    pathlib.Path(remote_path).mkdir(parents=True, exist_ok=True)

    with in_directory(remote_path):
        subprocess.call(["git", "init"])

        generate_file("README.md", f"Generated file for {name}")
        if context.text:
            generate_manifest(context)

        subprocess.call(["git", "add", "-A"])
        subprocess.call(["git", "commit", "-m", '"Initial commit"'])
        subprocess.call(["git", "tag", "-a", "v1", "-m", "'Some tag'"])
