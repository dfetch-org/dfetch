"""Steps for CMake import feature tests."""

# pylint: disable=function-redefined, missing-function-docstring, import-error, not-callable
# pyright: reportRedeclaration=false, reportAttributeAccessIssue=false, reportCallIssue=false

from behave import given  # pylint: disable=no-name-in-module

from features.steps.generic_steps import generate_file
from features.steps.git_steps import commit_all, create_repo


@given('a git repository with the file "{filepath}"')
def step_impl(context, filepath):
    create_repo()
    generate_file(filepath, context.text)
    commit_all("Initial commit")
