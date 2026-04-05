"""Unit tests for the JSONPath-based YamlDocument interface."""

import pytest

from dfetch.util.yaml import FieldLocation, NodeMatch, YamlDocument

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MANIFEST = """\
manifest:
  version: '0.0'

  projects:
    - name: myproject
      url: https://example.com/myproject
      branch: main

    - name: other
      url: https://example.com/other
      branch: develop
"""

_MANIFEST_WITH_COMMENT = """\
manifest:
  version: '0.0'

  projects:
    - name: myproject
      url: https://example.com/myproject  # source mirror
      branch: main  # integration branch
"""


# ---------------------------------------------------------------------------
# _parse_jsonpath
# ---------------------------------------------------------------------------


def test_parse_simple_member_path():
    steps = YamlDocument._parse_jsonpath("$.manifest.version")
    assert steps == ["manifest", "version"]


def test_parse_index_step():
    steps = YamlDocument._parse_jsonpath("$.manifest.projects[0]")
    assert steps == ["manifest", "projects", "0"]


def test_parse_filter_step():
    from dfetch.util.yaml import _FilterStep

    steps = YamlDocument._parse_jsonpath(
        '$.manifest.projects[?(@.name == "myproject")]'
    )
    assert steps == ["manifest", "projects", _FilterStep("name", "myproject")]


def test_parse_filter_with_sub_path():
    from dfetch.util.yaml import _FilterStep

    steps = YamlDocument._parse_jsonpath(
        '$.manifest.projects[?(@.name == "myproject")].branch'
    )
    assert steps == [
        "manifest",
        "projects",
        _FilterStep("name", "myproject"),
        "branch",
    ]


def test_parse_single_quote_filter():
    from dfetch.util.yaml import _FilterStep

    steps = YamlDocument._parse_jsonpath(
        "$.manifest.projects[?(@.name == 'myproject')]"
    )
    assert steps == ["manifest", "projects", _FilterStep("name", "myproject")]


def test_parse_filter_with_hyphenated_name():
    from dfetch.util.yaml import _FilterStep

    steps = YamlDocument._parse_jsonpath(
        '$.manifest.projects[?(@.name == "my-project")]'
    )
    assert steps == ["manifest", "projects", _FilterStep("name", "my-project")]


def test_parse_strips_trailing_whitespace():
    steps = YamlDocument._parse_jsonpath("$.manifest.version   ")
    assert steps == ["manifest", "version"]


def test_parse_missing_dollar_raises():
    with pytest.raises(ValueError, match="must start with"):
        YamlDocument._parse_jsonpath("manifest.version")


def test_parse_unsupported_syntax_raises():
    with pytest.raises(ValueError, match="Unsupported JSONPath"):
        YamlDocument._parse_jsonpath("$.manifest[*]")


# ---------------------------------------------------------------------------
# get() — scalar lookup
# ---------------------------------------------------------------------------


def test_get_simple_scalar():
    doc = YamlDocument(_MANIFEST)
    matches = doc.get("$.manifest.version")
    assert len(matches) == 1
    assert matches[0].value == "0.0"


def test_get_returns_node_match_type():
    doc = YamlDocument(_MANIFEST)
    matches = doc.get("$.manifest.version")
    assert isinstance(matches[0], NodeMatch)
    assert isinstance(matches[0].location, FieldLocation)


def test_get_location_is_accurate():
    doc = YamlDocument(_MANIFEST)
    # Line 2 (0-based: 1) is "  version: '0.0'"
    # '0.0' appears inside single quotes; YAML scalar value is 0.0
    matches = doc.get("$.manifest.version")
    assert matches[0].location.start_line == 1  # 0-based line 1


def test_get_filter_returns_scalar_of_matched_item():
    doc = YamlDocument(_MANIFEST)
    matches = doc.get('$.manifest.projects[?(@.name == "myproject")].branch')
    assert len(matches) == 1
    assert matches[0].value == "main"


def test_get_filter_name_field():
    doc = YamlDocument(_MANIFEST)
    matches = doc.get('$.manifest.projects[?(@.name == "myproject")].name')
    assert len(matches) == 1
    assert matches[0].value == "myproject"


def test_get_filter_second_item():
    doc = YamlDocument(_MANIFEST)
    matches = doc.get('$.manifest.projects[?(@.name == "other")].branch')
    assert len(matches) == 1
    assert matches[0].value == "develop"


def test_get_filter_no_match_returns_empty():
    doc = YamlDocument(_MANIFEST)
    matches = doc.get('$.manifest.projects[?(@.name == "nonexistent")].branch')
    assert matches == []


def test_get_nonexistent_scalar_returns_empty():
    doc = YamlDocument(_MANIFEST)
    assert doc.get("$.manifest.missing_key") == []


def test_get_mapping_node_returns_empty():
    """Addressing a mapping (not a scalar leaf) returns empty."""
    doc = YamlDocument(_MANIFEST)
    assert doc.get("$.manifest") == []


def test_get_sequence_node_returns_empty():
    doc = YamlDocument(_MANIFEST)
    assert doc.get("$.manifest.projects") == []


# ---------------------------------------------------------------------------
# set() — field update
# ---------------------------------------------------------------------------


def test_set_updates_existing_field():
    doc = YamlDocument(_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "branch", "feature-x")
    result = doc.dump()
    assert "branch: feature-x" in result


def test_set_adds_missing_field():
    doc = YamlDocument(_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "revision", "deadbeef")
    result = doc.dump()
    assert "revision: deadbeef" in result


def test_set_adds_nested_field():
    doc = YamlDocument(_MANIFEST)
    doc.set(
        '$.manifest.projects[?(@.name == "myproject")]',
        "integrity.hash",
        "sha256:abc123",
    )
    result = doc.dump()
    assert "integrity:" in result
    assert "hash: sha256:abc123" in result


def test_set_only_affects_matched_project():
    doc = YamlDocument(_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "revision", "abc123")
    result = doc.dump()
    # The other project must be untouched
    first_idx = result.index("- name: myproject")
    second_idx = result.index("- name: other")
    first_block = result[first_idx:second_idx]
    assert "revision" in first_block
    assert "revision" not in result[second_idx:]


def test_set_preserves_inline_comments():
    doc = YamlDocument(_MANIFEST_WITH_COMMENT)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "revision", "abc123")
    result = doc.dump()
    assert "# source mirror" in result
    assert "# integration branch" in result


def test_set_integer_like_value_is_quoted():
    """SVN revision numbers look like integers and must be YAML-quoted."""
    doc = YamlDocument(_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "revision", "176")
    result = doc.dump()
    assert "revision: '176'" in result


def test_set_noop_when_no_match():
    doc = YamlDocument(_MANIFEST)
    original = doc.dump()
    doc.set('$.manifest.projects[?(@.name == "ghost")]', "revision", "abc")
    assert doc.dump() == original


def test_set_simple_path_no_filter():
    doc = YamlDocument(_MANIFEST)
    doc.set("$.manifest", "version", "2.0")
    # "2.0" is quoted by the YAML scalar formatter to avoid float ambiguity
    assert "version: '2.0'" in doc.dump()


# ---------------------------------------------------------------------------
# dump()
# ---------------------------------------------------------------------------


def test_dump_roundtrips_unchanged_document():
    doc = YamlDocument(_MANIFEST)
    assert doc.dump() == _MANIFEST


def test_dump_reflects_set_changes():
    doc = YamlDocument(_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "branch", "new-branch")
    assert "new-branch" in doc.dump()
    assert "new-branch" not in _MANIFEST


# ---------------------------------------------------------------------------
# _find_field scope-leak regression
# ---------------------------------------------------------------------------

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
      revision: abc123
"""


def test_set_adds_field_to_first_project_not_found_in_second():
    """Adding a field absent in projects[0] must not match the same field in projects[1]."""
    doc = YamlDocument(_TWO_PROJECT_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "first")]', "revision", "deadbeef")
    result = doc.dump()

    # first project gains a revision
    first_end = result.index("- name: second")
    first_block = result[:first_end]
    assert "revision: deadbeef" in first_block

    # second project's revision is untouched
    second_block = result[first_end:]
    assert "revision: abc123" in second_block
    assert "revision: deadbeef" not in second_block


def test_get_field_absent_in_first_project_returns_empty():
    """get() for a field that exists only in projects[1] must return nothing for projects[0]."""
    doc = YamlDocument(_TWO_PROJECT_MANIFEST)
    matches = doc.get('$.manifest.projects[?(@.name == "first")].revision')
    assert matches == []


def test_get_field_present_in_second_project():
    doc = YamlDocument(_TWO_PROJECT_MANIFEST)
    matches = doc.get('$.manifest.projects[?(@.name == "second")].revision')
    assert len(matches) == 1
    assert matches[0].value == "abc123"


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------


def test_delete_removes_existing_scalar_field():
    doc = YamlDocument(_MANIFEST)
    doc.delete('$.manifest.projects[?(@.name == "myproject")]', "branch")
    result = doc.dump()
    # The myproject block should no longer contain branch
    myproject_end = result.index("- name: other")
    assert "branch:" not in result[:myproject_end]
    # Sibling project and other fields are untouched
    assert "url:" in result
    assert "branch: develop" in result


def test_delete_noop_when_field_absent():
    doc = YamlDocument(_MANIFEST)
    original = doc.dump()
    doc.delete('$.manifest.projects[?(@.name == "myproject")]', "revision")
    assert doc.dump() == original


def test_delete_noop_when_path_no_match():
    doc = YamlDocument(_MANIFEST)
    original = doc.dump()
    doc.delete('$.manifest.projects[?(@.name == "ghost")]', "branch")
    assert doc.dump() == original


def test_delete_removes_nested_block():
    manifest = """\
manifest:
  version: '0.0'
  projects:
    - name: pkg
      url: https://example.com
      vcs: archive
      integrity:
        hash: sha256:abc123
"""
    doc = YamlDocument(manifest)
    doc.delete('$.manifest.projects[?(@.name == "pkg")]', "integrity")
    result = doc.dump()
    assert "integrity:" not in result
    assert "hash:" not in result
    assert "url:" in result


def test_delete_only_affects_matched_project():
    doc = YamlDocument(_TWO_PROJECT_MANIFEST)
    doc.delete('$.manifest.projects[?(@.name == "second")]', "revision")
    result = doc.dump()
    first_end = result.index("- name: second")
    assert "branch: main" in result[:first_end]
    assert "revision" not in result[first_end:]


# ---------------------------------------------------------------------------
# Compact YAML sequence style (dfetch.yaml uses this)
# Items sit at the same indent as the parent key, e.g.:
#   projects:
#   - name: foo   ← same 2-space indent as 'projects:'
# ---------------------------------------------------------------------------

_COMPACT_MANIFEST = """\
manifest:
  version: '0.0'

  projects:
  - name: demo-magic
    repo-path: paxtonhare/demo-magic.git
    dst: doc/demo-magic
    src: '*.sh'

  - name: other-project
    repo-path: org/other.git
    dst: doc/other
"""


def test_compact_set_adds_new_field_inside_correct_project():
    """freeze adds branch/revision inside the project entry, not at end of file."""
    doc = YamlDocument(_COMPACT_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "demo-magic")]', "branch", "master")
    result = doc.dump()

    # branch must appear before the second project
    first_end = result.index("- name: other-project")
    assert "branch: master" in result[:first_end]
    # must not appear after the second project
    assert "branch: master" not in result[first_end:]


def test_compact_set_adds_revision_inside_correct_project():
    doc = YamlDocument(_COMPACT_MANIFEST)
    doc.set(
        '$.manifest.projects[?(@.name == "demo-magic")]',
        "revision",
        "2a2f439c",
    )
    result = doc.dump()

    first_end = result.index("- name: other-project")
    assert "revision: 2a2f439c" in result[:first_end]
    assert "revision" not in result[first_end:]


def test_compact_set_updates_existing_field():
    manifest = _COMPACT_MANIFEST.replace(
        "dst: doc/demo-magic", "dst: doc/demo-magic\n    branch: old"
    )
    doc = YamlDocument(manifest)
    doc.set('$.manifest.projects[?(@.name == "demo-magic")]', "branch", "new")
    result = doc.dump()

    first_end = result.index("- name: other-project")
    assert "branch: new" in result[:first_end]
    assert "branch: old" not in result


def test_compact_set_does_not_corrupt_file():
    """After set(), the manifest must still parse as valid YAML."""
    import yaml as _yaml

    doc = YamlDocument(_COMPACT_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "demo-magic")]', "branch", "master")
    doc.set('$.manifest.projects[?(@.name == "demo-magic")]', "revision", "abc123")
    parsed = _yaml.safe_load(doc.dump())
    projects = parsed["manifest"]["projects"]
    demo = next(p for p in projects if p["name"] == "demo-magic")
    assert demo["branch"] == "master"
    assert demo["revision"] == "abc123"
    other = next(p for p in projects if p["name"] == "other-project")
    assert "branch" not in other
    assert "revision" not in other


# ---------------------------------------------------------------------------
# 4-space indentation (auto-detected indent step)
# ---------------------------------------------------------------------------

_FOUR_SPACE_MANIFEST = """\
manifest:
    version: '0.0'

    projects:
        - name: myproject
          url: https://example.com/myproject
          branch: main

        - name: other
          url: https://example.com/other
"""

_FOUR_SPACE_COMPACT_MANIFEST = """\
manifest:
    version: '0.0'

    projects:
    - name: myproject
      url: https://example.com/myproject
      branch: main

    - name: other
      url: https://example.com/other
"""


def test_four_space_detects_indent_step():
    doc = YamlDocument(_FOUR_SPACE_MANIFEST)
    assert doc._indent_step == 4


def test_four_space_get_scalar():
    doc = YamlDocument(_FOUR_SPACE_MANIFEST)
    matches = doc.get("$.manifest.version")
    assert len(matches) == 1
    assert matches[0].value == "0.0"


def test_four_space_set_updates_existing_field():
    doc = YamlDocument(_FOUR_SPACE_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "branch", "feature-x")
    assert "branch: feature-x" in doc.dump()


def test_four_space_set_adds_missing_field():
    doc = YamlDocument(_FOUR_SPACE_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "revision", "deadbeef")
    result = doc.dump()
    first_end = result.index("- name: other")
    assert "revision: deadbeef" in result[:first_end]
    assert "revision" not in result[first_end:]


def test_four_space_set_only_affects_matched_project():
    doc = YamlDocument(_FOUR_SPACE_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "revision", "abc123")
    result = doc.dump()
    first_end = result.index("- name: other")
    assert "revision: abc123" in result[:first_end]
    assert "revision" not in result[first_end:]


def test_four_space_delete_removes_field():
    doc = YamlDocument(_FOUR_SPACE_MANIFEST)
    doc.delete('$.manifest.projects[?(@.name == "myproject")]', "branch")
    result = doc.dump()
    first_end = result.index("- name: other")
    assert "branch" not in result[:first_end]


def test_four_space_compact_adds_field_inside_correct_project():
    """4-space compact sequence: new field goes inside the right project."""
    doc = YamlDocument(_FOUR_SPACE_COMPACT_MANIFEST)
    doc.set('$.manifest.projects[?(@.name == "myproject")]', "revision", "abc123")
    result = doc.dump()
    first_end = result.index("- name: other")
    assert "revision: abc123" in result[:first_end]
    assert "revision" not in result[first_end:]
