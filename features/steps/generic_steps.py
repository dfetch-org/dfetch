"""Steps for features tests."""

import subprocess

from behave import then, when  # pylint: disable=no-name-in-module


@when('I run "{cmd}"')
def step_impl(context, cmd):
    """Call a command."""
    subprocess.call(cmd.split())


@then("it should generate the manifest '{name}'")
def step_impl(context, name):
    """Check a manifest."""
    with open(name, "r") as manifest:

        for actual, expected in zip(
            context.text.splitlines(True), manifest.readlines()
        ):

            assert (
                actual.strip() == expected.strip()
            ), f"Actual {actual.strip()} != Expected {expected.strip()}"
