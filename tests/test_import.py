"""Test the import command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from unittest.mock import patch

import pytest
import yaml

from dfetch.commands.import_ import Import, _determine_best_remotes
from dfetch.vcs.git import Submodule
from dfetch.vcs.svn import External

DEFAULT_ARGS = argparse.Namespace(non_recursive=False)

FIRST_SUBMODULE = Submodule(
    name="submod1",
    sha="1234",
    url="http://www.github.com/mod1.git",
    toplevel="",
    path="somepath1",
    branch="master",
    tag="",
)
SECOND_SUBMODULE = Submodule(
    name="submod2",
    sha="1234",
    url="http://www.github.com/mod2.git",
    toplevel="",
    path="somepath2",
    branch="",
    tag="v1.2.3",
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

    with patch("dfetch.project.svnsuperproject.SvnRepo.is_svn") as is_svn:
        with patch(
            "dfetch.project.gitsuperproject.GitLocalRepo.submodules"
        ) as mocked_submodules:
            with patch("dfetch.manifest.manifest.Manifest") as mocked_manifest:
                mocked_submodules.return_value = submodules
                with patch(
                    "dfetch.project.gitsuperproject.GitLocalRepo.is_git"
                ) as is_git:
                    is_git.return_value = True
                    is_svn.return_value = False

                    if len(submodules) == 0:
                        with pytest.raises(RuntimeError):
                            import_(argparse.Namespace())
                    else:
                        import_(argparse.Namespace())

                        mocked_manifest.from_yaml.assert_called()

                        yaml_text = mocked_manifest.from_yaml.call_args[0][0]
                        data = yaml.safe_load(yaml_text)
                        project_names = [
                            p["name"] for p in data["manifest"]["projects"]
                        ]
                        for submodule in submodules:
                            assert submodule.name in project_names

                        # Manifest should have been dumped
                        mocked_manifest.from_yaml.return_value.dump.assert_called()


def test_determine_best_remotes_covers_all_urls_at_max_remotes():
    """Every project URL must be covered, even when each needs its own remote.

    Reproduces the off-by-one in the combination-size loop: when the optimal
    solution needs the maximum number of distinct remotes (one per host), the
    largest combination was never evaluated, leaving one URL uncovered with its
    full-length URL retained in the manifest.
    """
    urls = {
        "https://github.com/a/x.git",
        "https://gitlab.com/b/y.git",
        "https://bitbucket.org/c/z.git",
        "https://example.com/d/w.git",
        "https://sourceforge.net/e/v.git",
    }

    remotes = _determine_best_remotes(urls)

    uncovered = [
        url for url in urls if not any(url.startswith(remote) for remote in remotes)
    ]
    assert not uncovered, f"URLs left without a matching remote: {uncovered}"


FIRST_EXTERNAL = External(
    name="external1",
    revision="1234",
    url="http://www.github.com/mod1/",
    toplevel="",
    path="somepath1",
    branch="trunk",
    tag="",
    src="some/sub/folder",
)
SECOND_EXTERNAL = External(
    name="external2",
    revision="1235",
    url="http://www.github.com/mod2/",
    toplevel="",
    path="somepath2",
    branch="",
    tag="0.0.2",
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

    with patch("dfetch.project.svnsuperproject.SvnRepo.is_svn") as is_svn:
        with patch(
            "dfetch.project.svnsuperproject.SvnRepo.externals"
        ) as mocked_externals:
            with patch("dfetch.manifest.manifest.Manifest") as mocked_manifest:
                with patch(
                    "dfetch.project.gitsuperproject.GitLocalRepo.is_git"
                ) as is_git:
                    is_git.return_value = False
                    is_svn.return_value = True
                    mocked_externals.return_value = externals

                    if len(externals) == 0:
                        with pytest.raises(RuntimeError):
                            import_(argparse.Namespace())
                    else:
                        import_(argparse.Namespace())

                        mocked_manifest.from_yaml.assert_called()

                        yaml_text = mocked_manifest.from_yaml.call_args[0][0]
                        data = yaml.safe_load(yaml_text)
                        project_names = [
                            p["name"] for p in data["manifest"]["projects"]
                        ]
                        for external in externals:
                            assert external.name in project_names

                        # Manifest should have been dumped
                        mocked_manifest.from_yaml.return_value.dump.assert_called()
