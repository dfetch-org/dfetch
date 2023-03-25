"""Steps for features tests."""

import os
import pathlib

from behave import given, then, when  # pylint: disable=no-name-in-module

from features.steps.generic_steps import check_file, generate_file, remote_server_path


def generate_manifest(context, name="dfetch.yaml", path=None):
    manifest = context.text.replace(
        "url: some-remote-server", f"url: file:///{remote_server_path(context)}"
    )
    generate_file(os.path.join(path or os.getcwd(), name), manifest)


@given("the manifest '{name}' in {path}")
@given("the manifest '{name}'")
@when("the manifest '{name}' is changed to")
@when("the manifest '{name}' in {path} is changed to")
def step_impl(context, name, path=None):
    if path:
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    generate_manifest(context, name, path)


@then("the manifest '{name}' is replaced with")
@then("it should generate the manifest '{name}'")
def step_impl(context, name):
    """Check a manifest."""
    check_file(name, context.text)


@given("the manifest '{name}' with the projects")
def step_impl(context, name):
    projects = "\n".join(f"      - name: {row['name']}" for row in context.table)
    manifest = f"""manifest:
    version: '0.0'
    remotes:
      - name: github-com-dfetch-org
        url-base: https://github.com/dfetch-org/test-repo

    projects:
{projects}
    """
    generate_file(os.path.join(os.getcwd(), name), manifest)
