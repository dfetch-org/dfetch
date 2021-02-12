import os
import shutil
import tempfile

from behave import fixture, use_fixture

from dfetch.util.util import safe_rmtree


@fixture
def tmpdir(context):
    # -- HINT: @behave.fixture is similar to @contextlib.contextmanager
    context.orig_cwd = os.getcwd()
    context.tmpdir = tempfile.mkdtemp()
    os.chdir(context.tmpdir)
    yield context.tmpdir
    # -- CLEANUP-FIXTURE PART:
    os.chdir(context.orig_cwd)
    safe_rmtree(context.tmpdir)


def before_feature(context, feature):
    use_fixture(tmpdir, context)
