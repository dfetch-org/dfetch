"""Test the import command."""
# mypy: ignore-errors
# flake8: noqa

import argparse
from typing import Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

import dfetch
from dfetch.commands.import_ import Import
from dfetch.manifest.manifest import Manifest
from dfetch.project.git import Submodule
from dfetch.project.svn import External

FIRST_SUBMODULE = Submodule(
    name="submod1",
    sha="1234",
    url="http://www.github.com/mod1.git",
    toplevel="",
    path="somepath1",
    branch="master",
)
SECOND_SUBMODULE = Submodule(
    name="submod2",
    sha="1234",
    url="http://www.github.com/mod2.git",
    toplevel="",
    path="somepath2",
    branch="master",
)


@pytest.mark.parametrize(
    "name, submodules",
    [
        ("empty", []),
        ("single_submodule", [FIRST_SUBMODULE]),
        (
            "two_submodules",
            [FIRST_SUBMODULE, SECOND_SUBMODULE],
        ),
    ],
)
def test_git_import(name, submodules):

    import_ = Import()

    with patch("dfetch.commands.import_.GitRepo.submodules") as mocked_submodules:
        with patch("dfetch.commands.import_.Manifest") as mocked_manifest:

            mocked_submodules.return_value = submodules

            if len(submodules) == 0:
                with pytest.raises(RuntimeError):
                    import_(argparse.Namespace)
            else:
                import_(argparse.Namespace)

                mocked_manifest.assert_called()

                args = mocked_manifest.call_args_list[0][0][0]

                for project_entry in args["projects"]:
                    assert project_entry.name in [subm.name for subm in submodules]

                # Manifest should have been dumped
                mocked_manifest.return_value.dump.assert_called()


FIRST_EXTERNAL = External(
    name="external1",
    revision="1234",
    url="http://www.github.com/mod1/",
    toplevel="",
    path="somepath1",
    branch="trunk",
    src="some/sub/folder",
)
SECOND_EXTERNAL = External(
    name="external2",
    revision="1235",
    url="http://www.github.com/mod2/",
    toplevel="",
    path="somepath2",
    branch="tags/0.0.2",
    src="some/sub/folder2/",
)


@pytest.mark.parametrize(
    "name, externals",
    [
        ("empty", []),
        ("single_external", [FIRST_EXTERNAL]),
        (
            "two_externals",
            [FIRST_EXTERNAL, SECOND_EXTERNAL],
        ),
    ],
)
def test_svn_import(name, externals):

    import_ = Import()

    with patch("dfetch.commands.import_.SvnRepo.check_path") as check_path:
        with patch("dfetch.commands.import_.SvnRepo.externals") as mocked_externals:
            with patch("dfetch.commands.import_.Manifest") as mocked_manifest:
                with patch("dfetch.commands.import_.GitRepo.check_path") as check_path_git:

                    check_path_git.return_value = False
                    check_path.return_value = True
                    mocked_externals.return_value = externals

                    if len(externals) == 0:
                        with pytest.raises(RuntimeError):
                            import_(argparse.Namespace)
                    else:
                        import_(argparse.Namespace)

                        mocked_manifest.assert_called()

                        args = mocked_manifest.call_args_list[0][0][0]

                        for project_entry in args["projects"]:
                            assert project_entry.name in [ext.name for ext in externals]

                        # Manifest should have been dumped
                        mocked_manifest.return_value.dump.assert_called()
