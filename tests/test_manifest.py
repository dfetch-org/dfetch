"""Test the manifest."""

# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import mock_open, patch

import pytest

from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.manifest.manifest import (
    Manifest,
    ManifestDict,
    ManifestEntryLocation,
    RequestedProjectNotFoundError,
    _find_project_block,
    _locate_project_name_line,
    _set_integrity_hash_in_block,
    _set_simple_field_in_block,
    _update_project_version_in_text,
)
from dfetch.util.yaml import append_field as _append_field
from dfetch.util.yaml import find_field as _find_field
from dfetch.util.yaml import update_value as _update_value
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


@pytest.mark.parametrize(
    "name, manifest, project_name, result",
    [
        (
            "match",
            " - name: foo",
            "foo",
            ManifestEntryLocation(line_number=1, start=10, end=12),
        ),
        (
            "no match",
            " - name: foo",
            "baz",
            RuntimeError,
        ),
        (
            "with comment",
            " - name: foo # some comment",
            "foo",
            ManifestEntryLocation(line_number=1, start=10, end=12),
        ),
        (
            "no spaces",
            " -name:foo #some comment",
            "foo",
            ManifestEntryLocation(line_number=1, start=8, end=10),
        ),
    ],
)
def test_get_manifest_location(name, manifest, project_name, result) -> None:

    manifest = Manifest(DICTIONARY_MANIFEST, text=manifest)

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


# --- _locate_project_name_line ---------------------------------------------


def test_locate_project_name_line_found() -> None:
    lines = _SIMPLE_MANIFEST.splitlines()
    result = _locate_project_name_line(lines, "myproject")
    assert result is not None
    line_idx, item_indent, name_start, name_end = result
    assert item_indent == 4
    assert lines[line_idx][name_start - 1 : name_end] == "myproject"


def test_locate_project_name_line_not_found() -> None:
    lines = _SIMPLE_MANIFEST.splitlines()
    assert _locate_project_name_line(lines, "nonexistent") is None


def test_locate_is_shared_by_find_name_and_find_block() -> None:
    """find_name_in_manifest and _find_project_block agree on the same line."""
    text = _SIMPLE_MANIFEST
    manifest = Manifest(
        {"version": "0.0", "projects": [{"name": "myproject", "url": "https://x.com"}]},
        text=text,
    )
    location = manifest.find_name_in_manifest("myproject")

    lines = text.splitlines(keepends=True)
    start, _end, _indent = _find_project_block(lines, "myproject")

    # Both should point to the same line (1-based vs 0-based).
    assert location.line_number == start + 1


# --- _find_project_block ---------------------------------------------------


def test_find_project_block_single() -> None:
    lines = _SIMPLE_MANIFEST.splitlines(keepends=True)
    start, end, item_indent = _find_project_block(lines, "myproject")
    assert item_indent == 4
    assert lines[start].startswith("    - name: myproject")
    # end should point past the block
    assert end == len(lines)


def test_find_project_block_first_of_two() -> None:
    lines = _TWO_PROJECT_MANIFEST.splitlines(keepends=True)
    start, end, item_indent = _find_project_block(lines, "first")
    assert item_indent == 4
    assert lines[start].startswith("    - name: first")
    # The blank line between projects is excluded from the block
    block_text = "".join(lines[start:end])
    assert "second" not in block_text


def test_find_project_block_second_of_two() -> None:
    lines = _TWO_PROJECT_MANIFEST.splitlines(keepends=True)
    start, _end, _indent = _find_project_block(lines, "second")
    assert lines[start].startswith("    - name: second")


def test_find_project_block_not_found() -> None:
    lines = _SIMPLE_MANIFEST.splitlines(keepends=True)
    with pytest.raises(RuntimeError, match="not found"):
        _find_project_block(lines, "nonexistent")


def test_find_project_block_comment_at_item_indent_does_not_end_block() -> None:
    """A comment at the same indent level as '- name:' must not split the block."""
    manifest = (
        "  - name: myproject\n"
        "    url: https://example.com\n"
        "  # revision: old-rev  <- comment at item-indent\n"
        "    branch: main\n"
    )
    lines = manifest.splitlines(keepends=True)
    start, end, item_indent = _find_project_block(lines, "myproject")
    block_text = "".join(lines[start:end])
    assert "branch: main" in block_text


# --- _set_simple_field_in_block --------------------------------------------


def test_set_simple_field_updates_existing() -> None:
    block = [
        "    - name: myproject\n",
        "      revision: oldrev\n",
        "      url: https://example.com\n",
    ]
    result = _set_simple_field_in_block(block, 6, "revision", "newrev")
    assert any("revision: newrev" in l for l in result)
    assert not any("oldrev" in l for l in result)


def test_set_simple_field_inserts_after_name() -> None:
    block = [
        "    - name: myproject\n",
        "      url: https://example.com\n",
    ]
    result = _set_simple_field_in_block(block, 6, "revision", "abc123")
    assert result[1] == "      revision: abc123\n"
    assert result[2] == "      url: https://example.com\n"


# --- _find_field -----------------------------------------------------------


def test_find_field_returns_index_when_present() -> None:
    block = [
        "    - name: myproject\n",
        "      revision: abc\n",
        "      url: https://example.com\n",
    ]
    assert _find_field(block, "revision", 6) == 1


def test_find_field_returns_none_when_absent() -> None:
    block = [
        "    - name: myproject\n",
        "      url: https://example.com\n",
    ]
    assert _find_field(block, "revision", 6) is None


def test_find_field_respects_start_end_bounds() -> None:
    block = [
        "    - name: myproject\n",
        "      revision: abc\n",
        "      url: https://example.com\n",
    ]
    # revision is at index 1, but we start searching at index 2 — should not find it
    assert _find_field(block, "revision", 6, start=2) is None
    # and with end=1 it is also excluded
    assert _find_field(block, "revision", 6, start=0, end=1) is None


def test_find_field_ignores_wrong_indent() -> None:
    block = [
        "    - name: myproject\n",
        "    revision: abc\n",  # indent 4, not 6
        "      url: https://example.com\n",
    ]
    assert _find_field(block, "revision", 6) is None


def test_find_field_skips_commented_out_field() -> None:
    """A '# field: value' line must not be matched — field is considered absent."""
    block = [
        "    - name: myproject\n",
        "      # branch: main\n",  # commented-out
        "      url: https://example.com\n",
    ]
    assert _find_field(block, "branch", 6) is None


def test_find_field_skips_commented_field_no_space() -> None:
    """'#field: value' (no space after #) must also not be matched."""
    block = [
        "    - name: myproject\n",
        "      #branch: main\n",
        "      url: https://example.com\n",
    ]
    assert _find_field(block, "branch", 6) is None


def test_find_field_finds_real_field_past_commented_one() -> None:
    """The live field after a commented-out duplicate is matched."""
    block = [
        "    - name: myproject\n",
        "      # branch: old\n",
        "      branch: new\n",
    ]
    assert _find_field(block, "branch", 6) == 2


# --- _update_value ---------------------------------------------------------


def test_update_value_replaces_inline_value() -> None:
    block = [
        "    - name: myproject\n",
        "      revision: old\n",
    ]
    result = _update_value(block, 1, "revision", "new")
    assert result[1] == "      revision: new\n"
    assert result[0] == block[0]  # untouched


def test_update_value_preserves_indent() -> None:
    block = ["        revision: old\n"]
    result = _update_value(block, 0, "revision", "newrev")
    assert result[0].startswith("        revision:")


def test_update_value_preserves_trailing_comment() -> None:
    block = ["      branch: main  # track the integration branch\n"]
    result = _update_value(block, 0, "branch", "main")
    assert result[0] == "      branch: main  # track the integration branch\n"


# --- _append_field ---------------------------------------------------------


def test_append_field_inserts_at_position() -> None:
    block = [
        "    - name: myproject\n",
        "      url: https://example.com\n",
    ]
    result = _append_field(block, "revision", "abc123", 6, after=1)
    assert result[1] == "      revision: abc123\n"
    assert result[2] == "      url: https://example.com\n"


def test_append_field_empty_value_omits_value_part() -> None:
    block = ["    - name: myproject\n"]
    result = _append_field(block, "integrity", "", 6, after=1)
    assert result[1] == "      integrity:\n"


# --- _set_integrity_hash_in_block ------------------------------------------


def test_set_integrity_hash_inserts_when_absent() -> None:
    block = [
        "    - name: myproject\n",
        "      url: https://example.com/archive.tar.gz\n",
        "      vcs: archive\n",
    ]
    result = _set_integrity_hash_in_block(block, 6, "sha256:abc123")
    joined = "".join(result)
    assert "integrity:" in joined
    assert "hash: sha256:abc123" in joined


def test_set_integrity_hash_updates_existing_hash() -> None:
    block = [
        "    - name: myproject\n",
        "      url: https://example.com/archive.tar.gz\n",
        "      vcs: archive\n",
        "      integrity:\n",
        "        hash: sha256:old\n",
    ]
    result = _set_integrity_hash_in_block(block, 6, "sha256:new")
    joined = "".join(result)
    assert "hash: sha256:new" in joined
    assert "sha256:old" not in joined


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

    # Verify the "first" block is unchanged by re-parsing and checking project count
    # with "revision" in the result.
    assert "revision:" in result  # second project got a revision

    # The "first" project block should have no revision field: find its block boundaries
    lines = result.splitlines(keepends=True)
    first_start, first_end, _ = _find_project_block(lines, "first")
    first_block_text = "".join(lines[first_start:first_end])
    assert "revision" not in first_block_text


def test_update_noop_when_no_version_fields() -> None:
    text = _SIMPLE_MANIFEST
    project = _make_project("myproject")  # no version fields
    result = _update_project_version_in_text(text, project)
    assert result == text


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
