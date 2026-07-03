"""General hooks for behave tests."""

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from behave import fixture, use_fixture
from rich.console import Console

from dfetch.util.util import safe_rm


@fixture
def tmpdir(context):
    """Create tempdir during test"""
    # -- HINT: @behave.fixture is similar to @contextlib.contextmanager
    context.orig_cwd = os.getcwd()
    context.tmpdir = tempfile.mkdtemp()
    os.chdir(context.tmpdir)
    context.remotes_dir_path = os.path.abspath(
        os.path.join(os.getcwd(), "some-remote-server")
    )
    yield context.tmpdir
    # -- CLEANUP-FIXTURE PART:
    os.chdir(context.orig_cwd)
    safe_rm(context.tmpdir, within=Path(context.tmpdir).parent)


def before_scenario(context, _):
    """Hook called before scenario is executed."""
    use_fixture(tmpdir, context)

    # Write to an explicit buffer instead of sys.stdout, so scenarios can
    # capture what a command prints to stdout separately from the log output.
    context.console = Console(
        record=True,
        force_terminal=True,
        width=1024,
        file=io.StringIO(),
    )

    context.newer_version_patcher = patch(
        "dfetch.commands.environment.newer_version_available",
        return_value=None,
    )
    context.newer_version_patcher.start()


def after_scenario(context, _):
    """Hook called after scenario is executed."""
    context.newer_version_patcher.stop()


def before_all(context):
    """Hook called before first test is run."""
    context.config.log_capture = True
    context.config.logging_format = "%(message)s"

    context.remotes_dir = "some-remote-server"

    os.environ["GIT_ALLOW_PROTOCOL"] = "file:http:https:ssh"
