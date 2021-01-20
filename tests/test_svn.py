"""Test the svn externals parsing command."""
# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import MagicMock, patch

import pytest

from dfetch.project.svn import SvnRepo, External

REPO_ROOT = "repo-root"
CWD = "C:\\mydir"

PINNED_SUBFOLDER = "Core/Modules - http://svn.mycompany.eu/MYCOMPANY/SomeModule/trunk/Core/Modules/Database@564 Database"
PINNED_SUBFOLDER_EXPECTATION = [
    External(
        name="Database",
        toplevel=CWD,
        path="Core/Modules/Database",
        revision="564",
        url="http://svn.mycompany.eu/MYCOMPANY/SomeModule",
        branch="",
        src="Core/Modules/Database",
    )
]

RELATIVE_TO_ROOT = """Data - -r 8349 ^/PROJECT-123/SOME-TOOL/trunk/python/Settings@8349 Settings
^/PROJECT-123/SOME-TOOL/trunk/path/Images@8571 Images"""
RELATIVE_TO_ROOT_EXPECTATIONS = [
    External(
        name="Settings",
        toplevel=CWD,
        path="Settings",
        revision="8349",
        url=REPO_ROOT + "/PROJECT-123/SOME-TOOL",
        branch="",
        src="python/Settings",
    ),
    External(
        name="Images",
        toplevel=CWD,
        path="Images",
        revision="8571",
        url=REPO_ROOT + "/PROJECT-123/SOME-TOOL",
        branch="",
        src="path/Images",
    ),
]

PINNED_SINGLE_FILE = """Module2 -
Module2/Binaries - ^/PROJECT-123/SOMEXE/tags/v0.3.0/SomeExe/bin/SomeExe.exe@6905 SomeExe.exe"""
PINNED_SINGLE_FILE_EXPECTATION = [
    External(
        name="SomeExe.exe",
        toplevel=CWD,
        path="Module2/Binaries/SomeExe.exe",
        revision="6905",
        url=REPO_ROOT + "/PROJECT-123/SOMEXE",
        branch="tags/v0.3.0",
        src="SomeExe/bin/SomeExe.exe",
    )
]

PINNED_MODULE_NO_SUBFOLDER = "Module3 - http://svn.mycompany.eu/MYCOMPANY/Jenkins/SomeProject/Resources/branches/my_branch@681 Module3"
PINNED_MODULE_NO_SUBFOLDER_EXPECTATION = [
    External(
        name="Module3",
        toplevel=CWD,
        path="Module3/Module3",
        revision="681",
        url="http://svn.mycompany.eu/MYCOMPANY/Jenkins/SomeProject/Resources",
        branch="branches/my_branch",
        src="",
    )
]


@pytest.mark.parametrize(
    "name, externals, expectations",
    [
        ("no_externals", [], []),
        ("pinned_subfolder", [PINNED_SUBFOLDER], PINNED_SUBFOLDER_EXPECTATION),
        ("relative_to_root", [RELATIVE_TO_ROOT], RELATIVE_TO_ROOT_EXPECTATIONS),
        ("pinned_single_file", [PINNED_SINGLE_FILE], PINNED_SINGLE_FILE_EXPECTATION),
        (
            "pinned_module_no_subfolder",
            [PINNED_MODULE_NO_SUBFOLDER],
            PINNED_MODULE_NO_SUBFOLDER_EXPECTATION,
        ),
        (
            "multiple",
            [
                PINNED_SUBFOLDER,
                RELATIVE_TO_ROOT,
                PINNED_SINGLE_FILE,
                PINNED_MODULE_NO_SUBFOLDER,
            ],
            PINNED_SUBFOLDER_EXPECTATION
            + RELATIVE_TO_ROOT_EXPECTATIONS
            + PINNED_SINGLE_FILE_EXPECTATION
            + PINNED_MODULE_NO_SUBFOLDER_EXPECTATION,
        ),
    ],
)
def test_externals(name, externals, expectations):

    with patch("dfetch.project.svn.run_on_cmdline") as run_on_cmdline_mock:
        with patch(
            "dfetch.project.svn.SvnRepo._get_info_from_target"
        ) as target_info_mock:
            with patch("dfetch.project.svn.os.getcwd") as cwd_mock:

                cmd_output = str(os.linesep * 2).join(externals)
                run_on_cmdline_mock().stdout = cmd_output.encode("utf-8")
                target_info_mock.return_value = {"Repository Root": REPO_ROOT}

                cwd_mock.return_value = CWD
                parsed_externals = SvnRepo.externals(MagicMock())

                for actual, expected in zip(parsed_externals, expectations):
                    assert actual == expected
