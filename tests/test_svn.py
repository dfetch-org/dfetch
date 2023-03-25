"""Test the svn externals parsing command."""
# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import MagicMock, patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.project.svn import External, SvnRepo
from dfetch.util.cmdline import SubprocessCommandError

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
        tag="",
        src="Core/Modules/Database",
    )
]

UNPINNED_NONSTD = (
    ". - http://svn.mycompany.eu/MYCOMPANY/SomeModule/Core/Modules/Database Database"
)
UNPINNED_NONSTD_EXPECTATION = [
    External(
        name="Database",
        toplevel=CWD,
        path="./Database",
        revision="",
        url="http://svn.mycompany.eu/MYCOMPANY/SomeModule/Core/Modules/Database",
        branch=" ",
        tag="",
        src="",
    )
]

RELATIVE_TO_ROOT = """Data - -r 8349 ^/PROJECT-123/SOME-TOOL/trunk/python/Settings@8349 Settings
^/PROJECT-123/SOME-TOOL/trunk/path/Images@8571 Images"""
RELATIVE_TO_ROOT_EXPECTATIONS = [
    External(
        name="Settings",
        toplevel=CWD,
        path="Data/Settings",
        revision="8349",
        url=REPO_ROOT + "/PROJECT-123/SOME-TOOL",
        branch="",
        tag="",
        src="python/Settings",
    ),
    External(
        name="Images",
        toplevel=CWD,
        path="Data/Images",
        revision="8571",
        url=REPO_ROOT + "/PROJECT-123/SOME-TOOL",
        branch="",
        tag="",
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
        branch="",
        tag="v0.3.0",
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
        branch="my_branch",
        tag="",
        src="",
    )
]


@pytest.mark.parametrize(
    "name, externals, expectations",
    [
        ("no_externals", [], []),
        ("pinned_subfolder", [PINNED_SUBFOLDER], PINNED_SUBFOLDER_EXPECTATION),
        ("unpinned_nonstd", [UNPINNED_NONSTD], UNPINNED_NONSTD_EXPECTATION),
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
                parsed_externals = SvnRepo.externals()

                for actual, expected in zip(parsed_externals, expectations):
                    assert actual == expected


@pytest.mark.parametrize(
    "name, cmd_result, expectation",
    [
        ("svn repo", ["Yep!"], True),
        ("not a svn repo", [SubprocessCommandError("", "", "", -1)], False),
        ("no svn", [RuntimeError()], False),
    ],
)
def test_check_path(name, cmd_result, expectation):
    with patch("dfetch.project.svn.run_on_cmdline") as run_on_cmdline_mock:
        run_on_cmdline_mock.side_effect = cmd_result

        assert SvnRepo.check_path() == expectation


@pytest.mark.parametrize(
    "name, project, cmd_result, expectation",
    [
        ("Ok url", ProjectEntry({"name": "proj1", "url": "some_url"}), ["Yep!"], True),
        (
            "Failed command",
            ProjectEntry({"name": "proj2", "url": "some_url"}),
            [SubprocessCommandError],
            False,
        ),
        (
            "No svn",
            ProjectEntry({"name": "proj3", "url": "some_url"}),
            [RuntimeError],
            False,
        ),
    ],
)
def test_check(name, project, cmd_result, expectation):
    with patch("dfetch.project.svn.run_on_cmdline") as run_on_cmdline_mock:
        run_on_cmdline_mock.side_effect = cmd_result

        assert SvnRepo(project).check() == expectation


SVN_INFO = """
Path: cpputest
URL: https://github.com/cpputest/cpputest
Relative URL: ^/
Repository Root: https://github.com/cpputest/cpputest
Repository UUID: 077c9a1d-76f4-0596-57cc-ce57b7db7bff
Revision: 3976
Node Kind: directory
Last Changed Author: bas.vodde
Last Changed Rev: 3976
Last Changed Date: 2021-02-06 13:57:00 +0100 (za, 06 feb 2021)

"""


def test_get_info():
    with patch("dfetch.project.svn.run_on_cmdline") as run_on_cmdline_mock:
        run_on_cmdline_mock.return_value.stdout = os.linesep.join(
            SVN_INFO.split("\n")
        ).encode()
        result = SvnRepo._get_info_from_target("bla")

        expectation = {
            "Path": "cpputest",
            "URL": "https://github.com/cpputest/cpputest",
            "Relative URL": "^/",
            "Repository Root": "https://github.com/cpputest/cpputest",
            "Repository UUID": "077c9a1d-76f4-0596-57cc-ce57b7db7bff",
            "Revision": "3976",
            "Node Kind": "directory",
            "Last Changed Author": "bas.vodde",
            "Last Changed Rev": "3976",
            "Last Changed Date": "2021-02-06 13:57:00 +0100 (za, 06 feb 2021)",
        }

        assert result == expectation


@pytest.fixture
def svn_repo():
    return SvnRepo(ProjectEntry({"name": "proj3", "url": "some_url"}))


def test_svn_repo_name(svn_repo):
    assert svn_repo.NAME == "svn"


def test_svn_repo_default_branch(svn_repo):
    assert svn_repo.DEFAULT_BRANCH == "trunk"


def test_svn_repo_split_url(svn_repo):
    url, branch, tag, src = svn_repo._split_url(
        "http://example.com/repo/trunk/src", "http://example.com/repo"
    )
    assert url == "http://example.com/repo"
    assert branch == ""  # empty for default branch
    assert tag == ""
    assert src == "src"

    url, branch, tag, src = svn_repo._split_url(
        "http://example.com/repo/branches/mybranch/src", "http://example.com/repo"
    )
    assert url == "http://example.com/repo"
    assert branch == "mybranch"
    assert tag == ""
    assert src == "src"

    url, branch, tag, src = svn_repo._split_url(
        "http://example.com/repo/nonstandard/folder/src", "http://example.com/repo"
    )
    assert url == "http://example.com/repo"
    assert branch == " "
    assert tag == ""
    assert src == "nonstandard/folder/src"

    url, branch, tag, src = svn_repo._split_url(
        "http://example.com/repo/tags/v1.0/src", "http://example.com/repo"
    )
    assert url == "http://example.com/repo"
    assert branch == ""
    assert tag == "v1.0"
    assert src == "src"
