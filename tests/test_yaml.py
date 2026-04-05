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
