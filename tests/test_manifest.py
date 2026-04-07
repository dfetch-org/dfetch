"""Test the manifest."""

# mypy: ignore-errors
# flake8: noqa
# pyright: ignore[reportAttributeAccessIssue]

import os
from typing import cast
from unittest.mock import mock_open, patch

import pytest

from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.manifest.manifest import (
    Manifest,
    ManifestBuilder,
    ManifestEntryLocation,
    RequestedProjectNotFoundError,
)
from dfetch.manifest.parse import find_manifest, get_submanifests
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote

BASIC_MANIFEST = """
manifest:
   version: 0

   remotes:
   - name: my-remote
     url-base: "http://www.myremote.com/"

   projects:
   - name: my-project
"""

MANIFEST_NO_PROJECTS = """
manifest:
   version: 0

   remotes:
   - name: my-remote
     url-base: "http://www.myremote.com/"
"""


MANIFEST_NO_REMOTES = """
manifest:
   version: 0

   projects:
   - name: my-project
     url: "http://www.somewhere.com"
"""


def given_manifest_from_text(text: str) -> Manifest:
    """Given the manifest as specified."""
    with patch("dfetch.manifest.manifest.open", mock_open(read_data=text)):
        return Manifest.from_file(DEFAULT_MANIFEST_NAME)


def test_can_read_version() -> None:
    """Test that the version can be read."""
    manifest = given_manifest_from_text(BASIC_MANIFEST)
    assert manifest.version == "0"


def test_no_projects() -> None:
    """Test that manifest without projects cannot be read."""

    with pytest.raises(RuntimeError):
        given_manifest_from_text(MANIFEST_NO_PROJECTS)


def test_no_remotes() -> None:
    """Test that manifest without remotes can be read."""

    manifest = given_manifest_from_text(MANIFEST_NO_REMOTES)

    assert len(manifest.projects) == 1
    assert manifest.projects[0].name == "my-project"
    assert manifest.projects[0].remote_url == "http://www.somewhere.com"
    assert len(manifest.remotes) == 0


def test_construct_from_yaml() -> None:
    """Test that manifest can be constructed from yaml text."""

    manifest = Manifest.from_yaml(BASIC_MANIFEST)
    assert manifest.version == "0"
    assert len(manifest.projects) == 1
    assert manifest.projects[0].name == "my-project"
    assert len(manifest.remotes) == 1
    assert manifest.remotes[0].name == "my-remote"


def test_no_manifests_found() -> None:
    with patch("dfetch.manifest.parse.find_file"):
        with pytest.raises(RuntimeError):
            find_manifest()


def test_multiple_manifests_found() -> None:
    with patch("dfetch.manifest.parse.find_file") as find_file_mock:
        find_file_mock.return_value = [DEFAULT_MANIFEST_NAME, "manifest2.yaml"]

        assert os.path.realpath(DEFAULT_MANIFEST_NAME) == find_manifest()


def test_single_manifest_found() -> None:
    with patch("dfetch.manifest.parse.find_file") as find_file_mock:
        find_file_mock.return_value = [DEFAULT_MANIFEST_NAME]

        joined = os.path.realpath(os.path.join(os.getcwd(), DEFAULT_MANIFEST_NAME))
        found = find_manifest()
        assert joined == found


@pytest.mark.parametrize(
    "name, manifest_paths",
    [
        (
            "no-submanifests",
            [],
        ),
        (
            "single-submanifest",
            ["some-manifest.yaml"],
        ),
        (
            "multi-submanifests",
            ["some-manifest.yaml", "some-other-manifest.yaml"],
        ),
    ],
)
def test_get_submanifests(name, manifest_paths) -> None:
    parent = ProjectEntry({"name": "name"})

    with patch("dfetch.manifest.parse.find_file") as find_file_mock:
        with patch("dfetch.manifest.parse.Manifest.from_file") as from_file_mock:
            find_file_mock.return_value = manifest_paths

            found_submanifests = get_submanifests([parent.name])

            assert len(found_submanifests) == len(manifest_paths)

            for path, call in zip(
                manifest_paths,
                from_file_mock.call_args_list,
            ):
                assert os.path.realpath(path) == call[0][0]


def test_suggestion_found() -> None:
    exception = RequestedProjectNotFoundError(["fIrst"], ["first", "other"])

    assert ["first"] == exception._guess_project(["fIrst"])


def test_suggestion_not_found() -> None:
    exception = RequestedProjectNotFoundError(["1234"], ["first", "other"])

    assert [] == exception._guess_project(["1234"])


def test_multiple_suggestions_found() -> None:
    exception = RequestedProjectNotFoundError(["irst", "otheR"], ["first", "other"])

    assert ["first", "other"] == exception._guess_project(["irst", "otheR"])


def test_single_suggestion_not_found() -> None:
    exception = RequestedProjectNotFoundError(["irst", "1234"], ["first", "other"])

    assert ["first"] == exception._guess_project(["irst", "1234"])


_FOO_MANIFEST_TEXT = (
    "manifest:\n"
    "  version: '0.0'\n"
    "  projects:\n"
    "  - name: foo\n"
    "    url: https://example.com\n"
)
_FOO_MANIFEST_TEXT_WITH_COMMENT = (
    "manifest:\n"
    "  version: '0.0'\n"
    "  projects:\n"
    "  - name: foo # some comment\n"
    "    url: https://example.com\n"
)


@pytest.mark.parametrize(
    "name, manifest_text, project_name, result",
    [
        (
            "match",
            _FOO_MANIFEST_TEXT,
            "foo",
            ManifestEntryLocation(line_number=4, start=11, end=13),
        ),
        (
            "no match",
            _FOO_MANIFEST_TEXT,
            "baz",
            RuntimeError,
        ),
        (
            "with comment",
            _FOO_MANIFEST_TEXT_WITH_COMMENT,
            "foo",
            ManifestEntryLocation(line_number=4, start=11, end=13),
        ),
    ],
)
def test_get_manifest_location(name, manifest_text, project_name, result) -> None:
    manifest = Manifest.from_yaml(manifest_text)

    if result == RuntimeError:
        with pytest.raises(RuntimeError):
            manifest.find_name_in_manifest(project_name)
    else:
        assert manifest.find_name_in_manifest(project_name) == result


# ---------------------------------------------------------------------------
# validate_destination – security: absolute paths must be rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dst",
    [
        "/etc/passwd",
        "/tmp/evil",
        "C:/Windows/System32",
        "C:\\Windows\\System32",
        "\\temp\\evil",
    ],
)
def test_validate_destination_rejects_absolute_paths(dst) -> None:
    with pytest.raises(ValueError, match="absolute"):
        Manifest.validate_destination(dst)


def test_validate_destination_rejects_dotdot() -> None:
    with pytest.raises(ValueError):
        Manifest.validate_destination("sub/../../../etc/passwd")


def test_validate_destination_accepts_relative() -> None:
    Manifest.validate_destination("external/mylib")  # must NOT raise


# ---------------------------------------------------------------------------
# In-place manifest text editing helpers
# ---------------------------------------------------------------------------

_SIMPLE_MANIFEST = """\
manifest:
  version: '0.0'

  projects:
    - name: myproject
      url: https://example.com/myproject
      branch: main
"""

_TWO_PROJECT_MANIFEST = """\
manifest:
  version: '0.0'

  projects:
    - name: first
      url: https://example.com/first
      branch: main

    - name: second
      url: https://example.com/second
      branch: develop
"""


# --- update_project_version -------------------------------------------------


def _make_project(name: str, **kwargs: str) -> ProjectEntry:
    """Helper: build a ProjectEntry with the given fields."""
    return ProjectEntry(cast(ProjectEntryDict, {"name": name, **kwargs}))


def _update(text: str, project: ProjectEntry) -> str:
    """Apply update_project_version and return the resulting text."""
    manifest = Manifest.from_yaml(text)
    manifest.update_project_version(project)
    return manifest._doc.as_yaml()


def test_update_adds_revision_preserves_layout() -> None:
    project = _make_project("myproject", revision="deadbeef" * 5, branch="main")
    result = _update(_SIMPLE_MANIFEST, project)
    # ruamel normalises sequence-in-mapping indent to 2 spaces.
    assert "  - name: myproject" in result
    # The revision is inserted.
    assert "revision:" in result
    # Original url line is still there.
    assert "url: https://example.com/myproject" in result


def test_update_second_project_does_not_touch_first() -> None:
    project = _make_project(
        "second", revision="abc123def456" * 3 + "abcd", branch="develop"
    )
    result = _update(_TWO_PROJECT_MANIFEST, project)

    assert "revision:" in result  # second project got a revision

    # The text between "- name: first" and "- name: second" must not contain "revision".
    first_idx = result.index("- name: first")
    second_idx = result.index("- name: second")
    first_block_text = result[first_idx:second_idx]
    assert "revision" not in first_block_text


def test_update_integer_like_revision_is_quoted() -> None:
    """SVN revisions look like integers and must be YAML-quoted."""
    project = _make_project("myproject", revision="176", branch="trunk")
    result = _update(_SIMPLE_MANIFEST, project)
    # The scalar '176' must be quoted in YAML to round-trip as a string.
    assert "revision: '176'" in result


def test_update_preserves_inline_comments_on_fields() -> None:
    """Inline comments on existing fields survive an in-place update."""
    text = (
        "manifest:\n"
        "  version: '0.0'\n"
        "  projects:\n"
        "    - name: myproject\n"
        "      url: https://example.com  # source mirror\n"
        "      branch: main  # track the integration branch\n"
    )
    project = _make_project("myproject", revision="deadbeef" * 5, branch="main")
    result = _update(text, project)
    assert "url: https://example.com" in result
    assert "# source mirror" in result
    assert "branch: main" in result
    assert "# track the integration branch" in result
    assert "revision:" in result


def test_update_commented_out_field_is_appended_not_matched() -> None:
    """A commented-out version field must be treated as absent; the real value is appended."""
    text = (
        "manifest:\n"
        "  version: '0.0'\n"
        "  projects:\n"
        "    - name: myproject\n"
        "      url: https://example.com\n"
        "      # branch: old-branch\n"
        "      branch: main\n"
    )
    project = _make_project("myproject", revision="deadbeef" * 5, branch="main")
    result = _update(text, project)
    # Commented-out line must survive unchanged
    assert "      # branch: old-branch" in result
    # The live branch line keeps its value
    assert "branch: main" in result
    assert "revision:" in result


def test_update_removes_stale_revision_when_pinned_by_tag() -> None:
    """update_project_version must delete stale 'revision' when the project is now pinned by tag."""
    text = (
        "manifest:\n"
        "  version: '0.0'\n"
        "  projects:\n"
        "    - name: myproject\n"
        "      url: https://example.com\n"
        "      revision: oldrev\n"
        "      branch: main\n"
    )
    # Project is now pinned exclusively by tag (revision and branch are empty).
    project = _make_project("myproject", tag="v1.2.3")
    result = _update(text, project)
    assert "tag: v1.2.3" in result
    assert "revision:" not in result
    assert "branch:" not in result


# ---------------------------------------------------------------------------
# Version field: always serialised as a quoted string
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "manifest_text, expected_version",
    [
        ("manifest:\n  version: 0\n  projects:\n  - name: p\n", "0"),
        ("manifest:\n  version: 0.0\n  projects:\n  - name: p\n", "0.0"),
        ("manifest:\n  version: '0.0'\n  projects:\n  - name: p\n", "0.0"),
        ("manifest:\n  version: '1.2'\n  projects:\n  - name: p\n", "1.2"),
    ],
)
def test_version_parsed_as_string(manifest_text: str, expected_version: str) -> None:
    """Version is stored as a string regardless of how it appears in YAML."""
    manifest = Manifest.from_yaml(manifest_text)
    assert manifest.version == expected_version


@pytest.mark.parametrize(
    "manifest_text",
    [
        "manifest:\n  version: 0\n  projects:\n  - name: p\n",
        "manifest:\n  version: 0.0\n  projects:\n  - name: p\n",
        "manifest:\n  version: '0.0'\n  projects:\n  - name: p\n",
    ],
)
def test_dump_writes_version_as_quoted_string(manifest_text: str) -> None:
    """dump must always write version as a quoted YAML string."""
    manifest = Manifest.from_yaml(manifest_text)
    result = manifest._doc.as_yaml()
    # The version value must appear quoted so that YAML parsers read it as a string.
    assert f"version: '{manifest.version}'" in result


# ---------------------------------------------------------------------------
# append_project_entry: in-memory cache must stay in sync
# ---------------------------------------------------------------------------


def test_append_project_entry_visible_in_projects() -> None:
    """manifest.projects must include the new entry immediately after append_project_entry."""
    manifest = Manifest.from_yaml(_SIMPLE_MANIFEST)
    new_project = _make_project("newproject", url="https://example.com/new")

    manifest.append_project_entry(new_project)

    names = [p.name for p in manifest.projects]
    assert "newproject" in names


def test_append_project_entry_check_name_uniqueness_sees_new_entry() -> None:
    """check_name_uniqueness must raise for a name added via append_project_entry."""
    manifest = Manifest.from_yaml(_SIMPLE_MANIFEST)
    new_project = _make_project("newproject", url="https://example.com/new")

    manifest.append_project_entry(new_project)

    with pytest.raises(ValueError, match="newproject"):
        manifest.check_name_uniqueness("newproject")


# ---------------------------------------------------------------------------
# ManifestBuilder
# ---------------------------------------------------------------------------

_GITHUB = Remote({"name": "github", "url-base": "https://github.com/"})


def _builder_with_one_project() -> ManifestBuilder:
    return ManifestBuilder().add_project_dict({"name": "mylib", "dst": "libs/mylib"})


def test_builder_returns_manifest() -> None:
    manifest = _builder_with_one_project().build()
    assert isinstance(manifest, Manifest)


def test_builder_sets_version() -> None:
    manifest = _builder_with_one_project().build()
    assert manifest.version == "0.0"


def test_builder_projects_are_accessible() -> None:
    manifest = (
        ManifestBuilder()
        .add_project_dict({"name": "alpha", "dst": "libs/alpha"})
        .add_project_dict({"name": "beta", "dst": "libs/beta"})
        .build()
    )
    names = [p.name for p in manifest.projects]
    assert names == ["alpha", "beta"]


def test_builder_remote_is_accessible() -> None:
    manifest = (
        ManifestBuilder()
        .add_remote(_GITHUB)
        .add_project_dict({"name": "mylib", "remote": "github"})
        .build()
    )
    assert len(manifest.remotes) == 1
    assert manifest.remotes[0].name == "github"


def test_builder_blank_line_after_version() -> None:
    manifest = _builder_with_one_project().build()
    assert "version: '0.0'\n\n" in manifest._doc.as_yaml()


def test_builder_blank_line_before_projects() -> None:
    manifest = _builder_with_one_project().build()
    assert "\n\n  projects:\n" in manifest._doc.as_yaml()


def test_builder_blank_line_before_remotes() -> None:
    manifest = (
        ManifestBuilder()
        .add_remote(_GITHUB)
        .add_project_dict({"name": "mylib"})
        .build()
    )
    assert "\n\n  remotes:\n" in manifest._doc.as_yaml()


def test_builder_blank_line_between_projects() -> None:
    manifest = (
        ManifestBuilder()
        .add_project_dict({"name": "alpha", "dst": "libs/alpha"})
        .add_project_dict({"name": "beta", "dst": "libs/beta"})
        .build()
    )
    assert "\n\n  - name: beta" in manifest._doc.as_yaml()


def test_builder_no_blank_line_before_first_project() -> None:
    manifest = (
        ManifestBuilder()
        .add_project_dict({"name": "alpha", "dst": "libs/alpha"})
        .add_project_dict({"name": "beta", "dst": "libs/beta"})
        .build()
    )
    yaml_text = manifest._doc.as_yaml()
    assert "projects:\n  - name: alpha" in yaml_text


def test_builder_blank_line_between_remotes() -> None:
    second = Remote({"name": "gitlab", "url-base": "https://gitlab.com/"})
    manifest = (
        ManifestBuilder()
        .add_remote(_GITHUB)
        .add_remote(second)
        .add_project_dict({"name": "mylib"})
        .build()
    )
    assert "\n\n  - name: gitlab" in manifest._doc.as_yaml()
