import os
import tempfile

from behave import fixture, use_fixture

from dfetch.util.util import safe_rmtree


@fixture
def tmpdir(context):
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
    safe_rmtree(context.tmpdir)


def before_scenario(context, scenario):
    use_fixture(tmpdir, context)


def before_all(context):
    context.config.log_capture = True
    context.config.logging_format = "%(message)s"

    context.remotes_dir = "some-remote-server"
