"""Test the svn externals parsing command."""

# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import MagicMock, patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.util.cmdline import SubprocessCommandError
from dfetch.vcs.svn import External, SshHostKeyError, SvnRemote, SvnRepo

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
        ("svn repo", [MagicMock(stdout=b"")], True),
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
        ("Ok url", [MagicMock(stdout=b"")], True),
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




def test_fetch_externals_returns_empty_when_no_externals():
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = []
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        assert subproject._fetch_externals(REPO_ROOT + "/trunk", "42") == []


def test_fetch_externals_forwards_path_and_revision():
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = []
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        complete_path = REPO_ROOT + "/trunk"
        subproject._fetch_externals(complete_path, "77")
        mock_ext.assert_called_once_with(complete_path, "77")


def test_fetch_externals_maps_externals_to_dependencies():
    externals_list = [
        External(
            name="mylib",
            toplevel="",
            path="vendor/mylib",
            revision="100",
            url=REPO_ROOT + "/libs",
            branch="",
            tag="",
            src="",
        ),
        External(
            name="utils",
            toplevel="",
            path="vendor/utils",
            revision="200",
            url=REPO_ROOT + "/utils",
            branch="devel",
            tag="",
            src="",
        ),
    ]
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = externals_list
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        result = subproject._fetch_externals(REPO_ROOT + "/trunk", "100")

        assert len(result) == 2

        assert result[0]["remote_url"] == REPO_ROOT + "/libs"
        assert result[0]["destination"] == "vendor/mylib"
        assert result[0]["branch"] == ""
        assert result[0]["tag"] == ""
        assert result[0]["revision"] == "100"
        assert result[0]["source_type"] == "svn-external"

        assert result[1]["remote_url"] == REPO_ROOT + "/utils"
        assert result[1]["destination"] == "vendor/utils"
        assert result[1]["branch"] == "devel"
        assert result[1]["revision"] == "200"
        assert result[1]["source_type"] == "svn-external"


def test_fetch_externals_preserves_tag_in_dependency():
    external = External(
        name="mylib",
        toplevel="",
        path="vendor/mylib",
        revision="300",
        url=REPO_ROOT + "/libs",
        branch="",
        tag="v2.0",
        src="",
    )
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = [external]
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        result = subproject._fetch_externals(REPO_ROOT + "/trunk", "300")

        assert result[0]["tag"] == "v2.0"
        assert result[0]["source_type"] == "svn-external"


def test_fetch_externals_nonstd_layout_preserves_space_branch():
    # A non-standard-layout external (URL contains no /trunk/, /branches/, or
    # /tags/) is represented with branch=" " by _split_url.  That sentinel must
    # reach the Dependency unchanged — it must NOT be collapsed to "" or "trunk"
    # by the display_branch substitution that only applies to the log line.
    external = External(
        name="Database",
        toplevel="",
        path="./Database",
        revision="",
        url="http://svn.mycompany.eu/MYCOMPANY/SomeModule/Core/Modules/Database",
        branch=" ",
        tag="",
        src="",
    )
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = [external]
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        result = subproject._fetch_externals(REPO_ROOT + "/trunk", "")

        assert result[0]["branch"] == " "
        assert result[0]["remote_url"] == (
            "http://svn.mycompany.eu/MYCOMPANY/SomeModule/Core/Modules/Database"
        )


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


@pytest.mark.parametrize(
    "method,url,call_args",
    [
        ("is_svn", "svn+ssh://svn.code.sf.net/project", ()),
        ("list_of_tags", "svn+ssh://svn.code.sf.net/project", ()),
        ("list_of_branches", "svn+ssh://svn.code.sf.net/project", ()),
        (
            "ls_tree",
            "svn+ssh://svn.code.sf.net/project",
            ("svn+ssh://svn.code.sf.net/project",),
        ),
    ],
)
def test_svn_remote_raises_hint_on_ssh_host_key_failure(method, url, call_args):
    """Test that SvnRemote methods raise SshHostKeyError with a hint on host-key failure."""
    stderr = "Host key verification failed."
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = SubprocessCommandError(["svn"], "", stderr, 1)

        with pytest.raises(SshHostKeyError, match="known hosts"):
            getattr(SvnRemote(url), method)(*call_args)


def test_get_info_from_target_raises_hint_on_ssh_host_key_failure():
    """Test that get_info_from_target raises SshHostKeyError instead of a generic error."""
    stderr = "Host key verification failed."
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = SubprocessCommandError(["svn", "info"], "", stderr, 1)

        with pytest.raises(SshHostKeyError, match="known hosts"):
            SvnRepo.get_info_from_target("svn+ssh://svn.code.sf.net/project")


@pytest.mark.parametrize(
    "method,url",
    [
        ("externals_from_url", "svn+ssh://svn.code.sf.net/project"),
        ("get_last_changed_revision", "svn+ssh://svn.code.sf.net/project"),
        ("export", "svn+ssh://svn.code.sf.net/project"),
        ("files_in_path", "svn+ssh://svn.code.sf.net/project"),
    ],
)
def test_svn_repo_raises_hint_on_ssh_host_key_failure(method, url):
    """Test that static SvnRepo methods raise SshHostKeyError on host-key failure."""
    stderr = "Host key verification failed."
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = SubprocessCommandError(["svn"], "", stderr, 1)

        with pytest.raises(SshHostKeyError, match="known hosts"):
            getattr(SvnRepo, method)(url)


def test_ssh_hint_includes_hostname():
    """Test that the host-key hint contains the hostname parsed from the URL."""
    stderr = "Host key verification failed."
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = SubprocessCommandError(["svn"], "", stderr, 1)

        with pytest.raises(SshHostKeyError, match="svn.code.sf.net"):
            SvnRemote("svn+ssh://svn.code.sf.net/project").is_svn()


def test_ssh_hint_includes_user_when_present_in_url():
    """Test that the host-key hint suggests ssh with the user from the URL."""
    stderr = "Host key verification failed."
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = SubprocessCommandError(["svn"], "", stderr, 1)

        with pytest.raises(SshHostKeyError, match="myuser@svn.code.sf.net"):
            SvnRemote("svn+ssh://myuser@svn.code.sf.net/project").is_svn()


def test_svn_ssh_env_has_batch_mode():
    """Test that the svn environment forces SSH BatchMode by default."""
    from dfetch.vcs.svn import _extend_env_for_non_interactive_mode

    _extend_env_for_non_interactive_mode.cache_clear()
    env = _extend_env_for_non_interactive_mode()
    assert "BatchMode=yes" in env["SVN_SSH"]


def test_svn_ssh_env_preserves_existing_batch_mode(monkeypatch):
    """Test that a user-configured BatchMode in SVN_SSH is left untouched."""
    from dfetch.vcs.svn import _extend_env_for_non_interactive_mode

    monkeypatch.setenv("SVN_SSH", "ssh -o BatchMode=yes -i /my/key")
    _extend_env_for_non_interactive_mode.cache_clear()
    env = _extend_env_for_non_interactive_mode()
    assert env["SVN_SSH"].count("BatchMode=yes") == 1
    assert "-i /my/key" in env["SVN_SSH"]


def test_run_svn_passes_non_interactive_env_to_subprocess():
    """Test that svn commands receive the non-interactive SSH environment."""
    from dfetch.vcs.svn import _extend_env_for_non_interactive_mode

    _extend_env_for_non_interactive_mode.cache_clear()
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.return_value = MagicMock(stdout=b"")

        SvnRepo.files_in_path("svn+ssh://svn.code.sf.net/project")

        env = mock_run.call_args.kwargs["env"]
        assert "BatchMode=yes" in env["SVN_SSH"]


def test_ssh_hint_on_authenticity_of_host_message():
    """Test that the 'authenticity of host' stderr variant also triggers the hint."""
    stderr = "The authenticity of host 'svn.code.sf.net' can't be established."
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = SubprocessCommandError(["svn"], "", stderr, 1)

        with pytest.raises(SshHostKeyError, match="known hosts"):
            SvnRemote("svn+ssh://svn.code.sf.net/project").is_svn()


def test_ssh_hint_without_url_omits_hostname_commands():
    """Test that the hint uses a placeholder when no hostname can be parsed."""
    stderr = "Host key verification failed."
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = SubprocessCommandError(["svn"], "", stderr, 1)

        with pytest.raises(SshHostKeyError, match="known hosts") as exc_info:
            SvnRepo(".").create_diff("1", "2", [])

        assert "ssh-keyscan <host>" in str(exc_info.value)


def test_browse_tree_raises_hint_on_ssh_host_key_failure():
    """Test that browse_tree surfaces SshHostKeyError instead of falling back to tags."""
    stderr = "Host key verification failed."
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.side_effect = SubprocessCommandError(["svn"], "", stderr, 1)

        with pytest.raises(SshHostKeyError, match="known hosts"):
            with SvnRemote("svn+ssh://svn.code.sf.net/project").browse_tree(
                "some-branch"
            ):
                pass


def test_create_diff_handles_non_utf8_diff_output():
    """Test that create_diff handles svn diff output that is not valid UTF-8."""
    diff = (
        b"Index: a.c\n"
        b"===================================================================\n"
        b"--- a.c\t(revision 1)\n"
        b"+++ a.c\t(working copy)\n"
        b"@@ -1 +1 @@\n"
        b"-old text \xe9\n"
        b"+new text \xe9\n"
    )
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.return_value = MagicMock(stdout=diff)

        patch_obj = SvnRepo(".").create_diff("1", "2", [])

        assert not patch_obj.is_empty()
