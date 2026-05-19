"""Test the svn externals parsing command."""

# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.util.cmdline import SubprocessCommandError
from dfetch.vcs.svn import External, SvnRemote, SvnRepo

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
        path="Database",
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

# -r REV URL NAME without a peg revision (@rev) in the URL.
EXPLICIT_REV_NO_PEG = (
    "lib - -r 500 http://svn.mycompany.eu/MYCOMPANY/SomeLib/trunk SomeLib"
)
EXPLICIT_REV_NO_PEG_EXPECTATION = [
    External(
        name="SomeLib",
        toplevel=CWD,
        path="lib/SomeLib",
        revision="500",
        url="http://svn.mycompany.eu/MYCOMPANY/SomeLib",
        branch="",
        tag="",
        src="",
    )
]

# Same -r form but with a subdirectory inside trunk, so src is also populated.
EXPLICIT_REV_NO_PEG_SUBFOLDER = (
    "vendor - -r 123 http://svn.mycompany.eu/MYCOMPANY/Framework/trunk/include Utils"
)
EXPLICIT_REV_NO_PEG_SUBFOLDER_EXPECTATION = [
    External(
        name="Utils",
        toplevel=CWD,
        path="vendor/Utils",
        revision="123",
        url="http://svn.mycompany.eu/MYCOMPANY/Framework",
        branch="",
        tag="",
        src="include",
    )
]

HYPHENATED_PATH = "libs/ui-kit - http://svn.mycompany.eu/MYCOMPANY/UIKit/trunk UIKit"
HYPHENATED_PATH_EXPECTATION = [
    External(
        name="UIKit",
        toplevel=CWD,
        path="libs/ui-kit/UIKit",
        revision="",
        url="http://svn.mycompany.eu/MYCOMPANY/UIKit",
        branch="",
        tag="",
        src="",
    )
]

AUTHENTICATED_URL_WITH_REV = (
    "lib - -r 100 svn+ssh://user@host/MYCOMPANY/SomeLib/trunk SomeLib"
)
AUTHENTICATED_URL_WITH_REV_EXPECTATION = [
    External(
        name="SomeLib",
        toplevel=CWD,
        path="lib/SomeLib",
        revision="100",
        url="svn+ssh://user@host/MYCOMPANY/SomeLib",
        branch="",
        tag="",
        src="",
    )
]

ROOT_LEVEL_EXTERNAL = ". - http://svn.mycompany.eu/MYCOMPANY/SomeLib/trunk SomeLib"
ROOT_LEVEL_EXTERNAL_EXPECTATION = [
    External(
        name="SomeLib",
        toplevel=CWD,
        path="SomeLib",
        revision="",
        url="http://svn.mycompany.eu/MYCOMPANY/SomeLib",
        branch="",
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
            "explicit_rev_no_peg",
            [EXPLICIT_REV_NO_PEG],
            EXPLICIT_REV_NO_PEG_EXPECTATION,
        ),
        (
            "explicit_rev_no_peg_subfolder",
            [EXPLICIT_REV_NO_PEG_SUBFOLDER],
            EXPLICIT_REV_NO_PEG_SUBFOLDER_EXPECTATION,
        ),
        (
            "hyphenated_path",
            [HYPHENATED_PATH],
            HYPHENATED_PATH_EXPECTATION,
        ),
        (
            "authenticated_url_with_rev",
            [AUTHENTICATED_URL_WITH_REV],
            AUTHENTICATED_URL_WITH_REV_EXPECTATION,
        ),
        (
            "root_level_external",
            [ROOT_LEVEL_EXTERNAL],
            ROOT_LEVEL_EXTERNAL_EXPECTATION,
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
    with patch("dfetch.vcs.svn.run_on_cmdline") as run_on_cmdline_mock:
        with patch("dfetch.vcs.svn.SvnRepo.get_info_from_target") as target_info_mock:
            with patch("dfetch.vcs.svn.os.chdir"):
                cmd_output = str(os.linesep * 2).join(externals)
                run_on_cmdline_mock().stdout = cmd_output.encode("utf-8")
                target_info_mock.return_value = {"Repository Root": REPO_ROOT}

                parsed_externals = SvnRepo(CWD).externals()

                for actual, expected in zip(
                    parsed_externals, expectations  # , strict=True
                ):
                    assert actual == expected


@pytest.mark.parametrize(
    "name, cmd_result, expectation",
    [
        ("svn repo", ["Yep!"], True),
        ("not a svn repo", [SubprocessCommandError([""], "", "", -1)], False),
        ("no svn", [RuntimeError()], False),
    ],
)
def test_check_path(name, cmd_result, expectation):
    with patch("dfetch.vcs.svn.run_on_cmdline") as run_on_cmdline_mock:
        run_on_cmdline_mock.side_effect = cmd_result

        assert SvnRepo().is_svn() == expectation


@pytest.mark.parametrize(
    "name, cmd_result, expectation",
    [
        ("Ok url", ["Yep!"], True),
        (
            "Failed command",
            [SubprocessCommandError],
            False,
        ),
        (
            "No svn",
            [RuntimeError],
            False,
        ),
    ],
)
def test_check(name, cmd_result, expectation):
    with patch("dfetch.vcs.svn.run_on_cmdline") as run_on_cmdline_mock:
        run_on_cmdline_mock.side_effect = cmd_result

        assert SvnRemote("some_url").is_svn() == expectation


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
    with patch("dfetch.vcs.svn.run_on_cmdline") as run_on_cmdline_mock:
        run_on_cmdline_mock.return_value.stdout = os.linesep.join(
            SVN_INFO.split("\n")
        ).encode()
        result = SvnRepo.get_info_from_target("bla")

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
def svn_subproject():
    return SvnSubProject(ProjectEntry({"name": "proj3", "url": "some_url"}))


def test_svn_subproject_name(svn_subproject):
    assert svn_subproject.NAME == "svn"


@pytest.fixture
def svn_repo():
    return SvnRepo()


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


# ---------------------------------------------------------------------------
# _normalize_url_prefix
# ---------------------------------------------------------------------------

_BASE_URL = "http://svn.example.com/repos/myproject"
_OTHER_LIB = "http://svn.other.com/repos/otherlib/trunk MyLib"


@pytest.mark.parametrize(
    "name, output, base_url, expected",
    [
        (
            "subdirectory",
            f"{_BASE_URL}/lib - {os.linesep}{_OTHER_LIB}",
            _BASE_URL,
            f"lib - {os.linesep}{_OTHER_LIB}",
        ),
        (
            "root_level",
            f"{_BASE_URL} - {os.linesep}{_OTHER_LIB}",
            _BASE_URL,
            f". - {os.linesep}{_OTHER_LIB}",
        ),
        (
            "trailing_slash_on_base_url",
            f"{_BASE_URL}/lib - {os.linesep}{_OTHER_LIB}",
            _BASE_URL + "/",
            f"lib - {os.linesep}{_OTHER_LIB}",
        ),
        (
            "unrelated_url_unchanged",
            f"http://other.com/repo - {os.linesep}{_OTHER_LIB}",
            _BASE_URL,
            f"http://other.com/repo - {os.linesep}{_OTHER_LIB}",
        ),
        (
            "multiple_entries",
            f"{_BASE_URL}/lib - {os.linesep}{_OTHER_LIB}"
            + os.linesep * 2
            + f"{_BASE_URL} - {os.linesep}http://svn.other.com/repos/framework/trunk Framework",
            _BASE_URL,
            f"lib - {os.linesep}{_OTHER_LIB}"
            + os.linesep * 2
            + f". - {os.linesep}http://svn.other.com/repos/framework/trunk Framework",
        ),
    ],
)
def test_normalize_url_prefix(name, output, base_url, expected):
    assert SvnRepo._normalize_url_prefix(output, base_url) == expected


# ---------------------------------------------------------------------------
# externals_from_url
# ---------------------------------------------------------------------------


def test_externals_from_url_omits_revision_when_not_given():
    with (
        patch("dfetch.vcs.svn.run_on_cmdline") as mock_run,
        patch("dfetch.vcs.svn.SvnRepo.get_info_from_target") as mock_info,
    ):
        mock_run.return_value.stdout = b""
        mock_info.return_value = {"Repository Root": REPO_ROOT}

        SvnRepo.externals_from_url(REPO_ROOT + "/trunk")

        cmd = mock_run.call_args[0][1]
        assert "--revision" not in cmd


def test_externals_from_url_adds_revision_flag_when_given():
    with (
        patch("dfetch.vcs.svn.run_on_cmdline") as mock_run,
        patch("dfetch.vcs.svn.SvnRepo.get_info_from_target") as mock_info,
    ):
        mock_run.return_value.stdout = b""
        mock_info.return_value = {"Repository Root": REPO_ROOT}

        SvnRepo.externals_from_url(REPO_ROOT + "/trunk", "42")

        cmd = mock_run.call_args[0][1]
        assert "--revision" in cmd
        assert "42" in cmd


@pytest.mark.parametrize(
    "name, error",
    [
        ("subprocess_error", SubprocessCommandError([""], "", "", -1)),
        ("runtime_error", RuntimeError("not an SVN repo")),
    ],
)
def test_externals_from_url_propagates_error(name, error):
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = error
        with pytest.raises(type(error)):
            SvnRepo.externals_from_url(REPO_ROOT + "/trunk")


def test_externals_from_url_normalizes_url_prefix_and_parses():
    base = "http://svn.example.com/repos/myproject/trunk"
    raw = (
        f"{base}/vendor - "
        + os.linesep
        + "http://svn.example.com/repos/libs/trunk@100 mylib"
    )
    with (
        patch("dfetch.vcs.svn.run_on_cmdline") as mock_run,
        patch("dfetch.vcs.svn.SvnRepo.get_info_from_target") as mock_info,
    ):
        mock_run.return_value.stdout = raw.encode()
        mock_info.return_value = {"Repository Root": "http://svn.example.com/repos"}

        result = SvnRepo.externals_from_url(base)

        assert len(result) == 1
        assert result[0].name == "mylib"
        assert result[0].revision == "100"
        assert result[0].path == "vendor/mylib"
        assert result[0].url == "http://svn.example.com/repos/libs"


def test_externals_from_url_nonstd_layout_branch_is_space():
    # When the external URL has no /trunk/, /branches/, or /tags/ segment,
    # _split_url returns branch=" " (non-standard layout sentinel).  Confirm
    # this flows through the full externals_from_url pipeline.
    base = "http://svn.example.com/repos/myproject/trunk"
    nonstd_url = "http://svn.mycompany.eu/MYCOMPANY/SomeModule/Core/Modules/Database"
    raw = f"{base} - {os.linesep}{nonstd_url} Database"
    with (
        patch("dfetch.vcs.svn.run_on_cmdline") as mock_run,
        patch("dfetch.vcs.svn.SvnRepo.get_info_from_target") as mock_info,
    ):
        mock_run.return_value.stdout = raw.encode()
        mock_info.return_value = {"Repository Root": "http://svn.example.com/repos"}

        result = SvnRepo.externals_from_url(base)

        assert len(result) == 1
        assert result[0].name == "Database"
        assert result[0].branch == " "
        assert result[0].url == nonstd_url
        assert result[0].revision == ""
        assert result[0].path == "Database"
