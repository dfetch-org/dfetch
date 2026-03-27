"""Tests for CMake FetchContent / ExternalProject import support."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dfetch.commands.import_ import (
    Import,
    _classify_git_ref,
    _cmake_dep_to_project_entry,
)
from dfetch.vcs.cmake import (
    CMakeExternalDependency,
    _extract_body,
    _find_dependencies_in_text,
    _parse_body,
)

# ---------------------------------------------------------------------------
# cmake.py unit tests
# ---------------------------------------------------------------------------

FETCH_CONTENT_GIT = """\
FetchContent_Declare(json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG        v3.11.2
)
"""

FETCH_CONTENT_GIT_SHA = """\
FetchContent_Declare(mylib
    GIT_REPOSITORY https://github.com/example/mylib.git
    GIT_TAG        a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
)
"""

EXTERNAL_PROJECT_URL = """\
ExternalProject_Add(catch2
    URL      https://github.com/catchorg/Catch2/archive/v3.3.2.tar.gz
    URL_HASH SHA256=8361907...
)
"""

EXTERNAL_PROJECT_GIT = """\
ExternalProject_Add(fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.2.1
)
"""

NO_URL_DECLARE = """\
FetchContent_Declare(internal
    SOURCE_DIR ${CMAKE_SOURCE_DIR}/third_party/internal
)
"""

COMMENTED_OUT = """\
# FetchContent_Declare(ignored
#     GIT_REPOSITORY https://example.com/ignored.git
#     GIT_TAG v1
# )
FetchContent_Declare(real
    GIT_REPOSITORY https://example.com/real.git
    GIT_TAG        v2
)
"""

MULTIPLE_DEPS = """\
FetchContent_Declare(dep1
    GIT_REPOSITORY https://github.com/org/dep1.git
    GIT_TAG        v1.0
)

ExternalProject_Add(dep2
    URL https://example.com/dep2.tar.gz
)
"""

CASE_INSENSITIVE = """\
fetchcontent_declare(myDep
    git_repository https://github.com/org/mydep.git
    git_tag        main
)
"""


def test_fetch_content_git_parsed():
    deps = list(_find_dependencies_in_text(FETCH_CONTENT_GIT))
    assert len(deps) == 1
    dep = deps[0]
    assert dep.name == "json"
    assert dep.git_repository == "https://github.com/nlohmann/json.git"
    assert dep.git_tag == "v3.11.2"
    assert dep.url == ""


def test_external_project_url_parsed():
    deps = list(_find_dependencies_in_text(EXTERNAL_PROJECT_URL))
    assert len(deps) == 1
    dep = deps[0]
    assert dep.name == "catch2"
    assert dep.url == "https://github.com/catchorg/Catch2/archive/v3.3.2.tar.gz"
    assert dep.git_repository == ""


def test_external_project_git_parsed():
    deps = list(_find_dependencies_in_text(EXTERNAL_PROJECT_GIT))
    assert len(deps) == 1
    dep = deps[0]
    assert dep.name == "fmt"
    assert dep.git_repository == "https://github.com/fmtlib/fmt.git"
    assert dep.git_tag == "10.2.1"


def test_dependency_without_url_is_skipped():
    deps = list(_find_dependencies_in_text(NO_URL_DECLARE))
    assert deps == []


def test_commented_declarations_are_ignored():
    deps = list(_find_dependencies_in_text(COMMENTED_OUT))
    assert len(deps) == 1
    assert deps[0].name == "real"
    assert deps[0].git_repository == "https://example.com/real.git"


def test_multiple_dependencies_in_one_file():
    deps = list(_find_dependencies_in_text(MULTIPLE_DEPS))
    assert len(deps) == 2
    names = {d.name for d in deps}
    assert names == {"dep1", "dep2"}


def test_commands_are_case_insensitive():
    deps = list(_find_dependencies_in_text(CASE_INSENSITIVE))
    assert len(deps) == 1
    assert deps[0].name == "myDep"


def test_url_hash_not_mistaken_for_url():
    cmake = """\
ExternalProject_Add(foo
    URL      https://example.com/foo.tar.gz
    URL_HASH SHA256=abc123
)
"""
    deps = list(_find_dependencies_in_text(cmake))
    assert len(deps) == 1
    assert deps[0].url == "https://example.com/foo.tar.gz"


def test_empty_text_yields_no_deps():
    assert list(_find_dependencies_in_text("")) == []


def test_extract_body_balanced_parens():
    text = "outer(inner(a) b)"
    # start at position after first '(', i.e. index 6
    body = _extract_body(text, 6)
    assert body == "inner(a) b"


def test_parse_body_none_when_no_name():
    assert _parse_body("") is None


def test_parse_body_none_when_no_url():
    result = _parse_body("myname SOME_FLAG ON")
    assert result is None


# ---------------------------------------------------------------------------
# _classify_git_ref tests
# ---------------------------------------------------------------------------


def test_classify_40_char_hex_as_revision():
    sha = "a" * 40
    tag, revision = _classify_git_ref(sha)
    assert tag == ""
    assert revision == sha


def test_classify_short_ref_as_tag():
    tag, revision = _classify_git_ref("v1.2.3")
    assert tag == "v1.2.3"
    assert revision == ""


def test_classify_branch_name_as_tag():
    tag, revision = _classify_git_ref("main")
    assert tag == "main"
    assert revision == ""


def test_classify_empty_ref():
    tag, revision = _classify_git_ref("")
    assert tag == ""
    assert revision == ""


# ---------------------------------------------------------------------------
# _cmake_dep_to_project_entry tests
# ---------------------------------------------------------------------------


def test_git_dep_uses_git_repository_as_url():
    dep = CMakeExternalDependency(
        name="json",
        git_repository="https://github.com/nlohmann/json.git",
        git_tag="v3.11.2",
    )
    entry = _cmake_dep_to_project_entry(dep)
    assert entry is not None
    assert entry.name == "json"
    assert "v3.11.2" in str(entry.as_yaml().get("tag", ""))


def test_url_dep_uses_url():
    dep = CMakeExternalDependency(
        name="catch2",
        url="https://example.com/catch2.tar.gz",
    )
    entry = _cmake_dep_to_project_entry(dep)
    assert entry is not None
    assert entry.name == "catch2"


def test_dep_with_sha_uses_revision():
    sha = "b" * 40
    dep = CMakeExternalDependency(
        name="lib",
        git_repository="https://example.com/lib.git",
        git_tag=sha,
    )
    entry = _cmake_dep_to_project_entry(dep)
    assert entry is not None
    yaml = entry.as_yaml()
    assert yaml.get("revision") == sha
    assert "tag" not in yaml


def test_dep_without_url_returns_none():
    dep = CMakeExternalDependency(name="nourl")
    assert _cmake_dep_to_project_entry(dep) is None


# ---------------------------------------------------------------------------
# Import command integration tests with --detect-cmake
# ---------------------------------------------------------------------------


def _make_cmake_dep(name="json", repo="https://github.com/nlohmann/json.git", tag="v3.11.2"):
    return CMakeExternalDependency(name=name, git_repository=repo, git_tag=tag)


def test_import_with_detect_cmake_creates_manifest():
    import_ = Import()
    cmake_deps = [_make_cmake_dep()]

    with patch("dfetch.project.svnsuperproject.SvnRepo.is_svn", return_value=False):
        with patch("dfetch.project.gitsuperproject.GitLocalRepo.is_git", return_value=True):
            with patch(
                "dfetch.project.gitsuperproject.GitLocalRepo.submodules", return_value=[]
            ):
                with patch(
                    "dfetch.commands.import_.find_cmake_dependencies",
                    return_value=cmake_deps,
                ):
                    with patch("dfetch.commands.import_.Manifest") as mocked_manifest:
                        import_(argparse.Namespace(detect_cmake=True))

                        mocked_manifest.assert_called_once()
                        args = mocked_manifest.call_args_list[0][0][0]
                        project_names = [p.name for p in args["projects"]]
                        assert "json" in project_names
                        mocked_manifest.return_value.dump.assert_called_once()


def test_import_without_detect_cmake_ignores_cmake_files():
    import_ = Import()

    with patch("dfetch.project.svnsuperproject.SvnRepo.is_svn", return_value=False):
        with patch("dfetch.project.gitsuperproject.GitLocalRepo.is_git", return_value=True):
            with patch(
                "dfetch.project.gitsuperproject.GitLocalRepo.submodules", return_value=[]
            ):
                with patch(
                    "dfetch.commands.import_.find_cmake_dependencies"
                ) as mock_cmake:
                    with pytest.raises(RuntimeError):
                        import_(argparse.Namespace(detect_cmake=False))
                    mock_cmake.assert_not_called()


def test_import_cmake_combined_with_submodules():
    """CMake deps are appended to any existing submodule-derived projects."""
    from dfetch.vcs.git import Submodule

    submodule = Submodule(
        name="existing",
        sha="1234",
        url="https://github.com/org/existing.git",
        toplevel="",
        path="existing",
        branch="main",
        tag="",
    )
    cmake_dep = _make_cmake_dep(name="cmake-dep")

    import_ = Import()
    with patch("dfetch.project.svnsuperproject.SvnRepo.is_svn", return_value=False):
        with patch("dfetch.project.gitsuperproject.GitLocalRepo.is_git", return_value=True):
            with patch(
                "dfetch.project.gitsuperproject.GitLocalRepo.submodules",
                return_value=[submodule],
            ):
                with patch(
                    "dfetch.commands.import_.find_cmake_dependencies",
                    return_value=[cmake_dep],
                ):
                    with patch("dfetch.commands.import_.Manifest") as mocked_manifest:
                        import_(argparse.Namespace(detect_cmake=True))

                        args = mocked_manifest.call_args_list[0][0][0]
                        project_names = [p.name for p in args["projects"]]
                        assert "existing" in project_names
                        assert "cmake-dep" in project_names


def test_import_cmake_no_deps_and_no_submodules_raises():
    import_ = Import()
    with patch("dfetch.project.svnsuperproject.SvnRepo.is_svn", return_value=False):
        with patch("dfetch.project.gitsuperproject.GitLocalRepo.is_git", return_value=True):
            with patch(
                "dfetch.project.gitsuperproject.GitLocalRepo.submodules", return_value=[]
            ):
                with patch(
                    "dfetch.commands.import_.find_cmake_dependencies", return_value=[]
                ):
                    with pytest.raises(RuntimeError):
                        import_(argparse.Namespace(detect_cmake=True))
