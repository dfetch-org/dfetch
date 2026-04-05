"""Test the manifest."""

# mypy: ignore-errors
# flake8: noqa
# pyright: ignore[reportAttributeAccessIssue]

import os
from unittest.mock import mock_open, patch

import pytest

from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.manifest.manifest import (
    Manifest,
    ManifestDict,
    ManifestEntryLocation,
    RequestedProjectNotFoundError,
    _update_project_version_in_text,
)
from dfetch.manifest.parse import find_manifest, get_submanifests
from dfetch.manifest.project import ProjectEntry

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

DICTIONARY_MANIFEST = ManifestDict(
    version="0",
    remotes=[{"name": "my-remote", "url-base": "http://www.myremote.com/"}],
    projects=[{"name": "my-project"}],
)


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

    with pytest.raises(KeyError):
        given_manifest_from_text(MANIFEST_NO_PROJECTS)


def test_no_remotes() -> None:
    """Test that manifest without remotes can be read."""

    manifest = given_manifest_from_text(MANIFEST_NO_REMOTES)

    assert len(manifest.projects) == 1
    assert manifest.projects[0].name == "my-project"
    assert manifest.projects[0].remote_url == "http://www.somewhere.com"
    assert len(manifest._remotes) == 0


def test_construct_from_dict() -> None:
    """Test that manifest can be constructed from dictionary."""

    manifest = Manifest(DICTIONARY_MANIFEST)
    assert manifest.version == "0"
    assert len(manifest.projects) == 1
    assert manifest.projects[0].name == "my-project"
    assert len(manifest._remotes) == 1
    assert next(iter(manifest._remotes.values())).name == "my-remote"


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
        with patch("dfetch.manifest.parse.parse") as parse_mock:
            find_file_mock.return_value = manifest_paths

            found_submanifests = get_submanifests([parent.name])

            assert len(found_submanifests) == len(manifest_paths)

            for path, call in zip(
                manifest_paths,
                parse_mock.call_args_list,  # , strict=True
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
    manifest = Manifest(DICTIONARY_MANIFEST, text=manifest_text)

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


# --- _update_project_version_in_text ---------------------------------------


def _make_project(name: str, **kwargs) -> ProjectEntry:
    """Helper: build a ProjectEntry with the given fields."""
    data = {"name": name}
    data.update(kwargs)
    return ProjectEntry(data)  # type: ignore[arg-type]


def test_update_adds_revision_preserves_layout() -> None:
    text = _SIMPLE_MANIFEST
    project = _make_project("myproject", revision="deadbeef" * 5, branch="main")
    result = _update_project_version_in_text(text, project)
    # The layout (4-space indent for "- name:") is preserved.
    assert "    - name: myproject" in result
    # The revision is inserted.
    assert "revision:" in result
    # Original url line is still there.
    assert "url: https://example.com/myproject" in result


def test_update_second_project_does_not_touch_first() -> None:
    text = _TWO_PROJECT_MANIFEST
    project = _make_project(
        "second", revision="abc123def456" * 3 + "abcd", branch="develop"
    )
    result = _update_project_version_in_text(text, project)

    assert "revision:" in result  # second project got a revision

    # The text between "- name: first" and "- name: second" must not contain "revision".
    first_idx = result.index("- name: first")
    second_idx = result.index("- name: second")
    first_block_text = result[first_idx:second_idx]
    assert "revision" not in first_block_text


def test_update_stale_version_keys_removed_when_project_has_none() -> None:
    """Stale version keys in the manifest are removed when the project carries none."""
    text = _SIMPLE_MANIFEST  # contains branch: main
    project = _make_project("myproject")  # no version fields at all
    result = _update_project_version_in_text(text, project)
    assert "branch:" not in result
    assert "revision:" not in result
    assert "tag:" not in result
    # Non-version fields are untouched
    assert "url:" in result


def test_update_integer_like_revision_is_quoted() -> None:
    """SVN revisions look like integers and must be YAML-quoted."""
    text = _SIMPLE_MANIFEST
    project = _make_project("myproject", revision="176", branch="trunk")
    result = _update_project_version_in_text(text, project)
    # The scalar '176' must be quoted in YAML to round-trip as a string.
    assert "revision: '176'" in result


def test_update_preserves_inline_comments_on_fields() -> None:
    """Inline comments on existing fields survive an in-place freeze."""
    text = (
        "manifest:\n"
        "  version: '0.0'\n"
        "  projects:\n"
        "    - name: myproject\n"
        "      url: https://example.com  # source mirror\n"
        "      branch: main  # track the integration branch\n"
    )
    project = _make_project("myproject", revision="deadbeef" * 5, branch="main")
    result = _update_project_version_in_text(text, project)
    assert "url: https://example.com  # source mirror" in result
    assert "branch: main  # track the integration branch" in result
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
    result = _update_project_version_in_text(text, project)
    # Commented-out line must survive unchanged
    assert "      # branch: old-branch" in result
    # The live branch line keeps its comment-free value
    assert "      branch: main" in result
    # revision is inserted as a new field, not used to update the comment
    assert result.count("branch:") == 2  # comment + live field
    assert "revision:" in result


def test_update_comment_at_item_indent_does_not_break_block() -> None:
    """A comment at item-indent level inside a block must not end the block early."""
    text = (
        "manifest:\n"
        "  version: '0.0'\n"
        "  projects:\n"
        "    - name: myproject\n"
        "      url: https://example.com\n"
        "    # old pinned version\n"
        "      branch: main\n"
    )
    project = _make_project("myproject", revision="deadbeef" * 5, branch="main")
    result = _update_project_version_in_text(text, project)
    # The comment at item-indent is preserved verbatim
    assert "    # old pinned version" in result
    # branch is updated in-place, not duplicated
    assert result.count("branch:") == 1
    assert "revision:" in result


def test_update_stale_revision_removed_when_project_switches_to_tag() -> None:
    """When a project changes from revision to tag, the stale revision key is deleted."""
    text = (
        "manifest:\n"
        "  version: '0.0'\n"
        "  projects:\n"
        "    - name: myproject\n"
        "      url: https://example.com\n"
        "      revision: deadbeefdeadbeef\n"
        "      branch: main\n"
    )
    project = _make_project("myproject", tag="v1.0.0")
    result = _update_project_version_in_text(text, project)
    assert "tag: v1.0.0" in result
    assert "revision:" not in result
    assert "branch:" not in result
