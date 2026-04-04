"""Generic YAML text-editing utilities.

These helpers operate on plain lists of text lines and know nothing about
dfetch-specific concepts.  They are used by :mod:`dfetch.manifest.manifest`
to edit manifest files in-place while preserving comments and layout.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


@dataclass
class YamlNodeLocation:
    """Location of a YAML node in a text document."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


def yaml_scalar(value: str) -> str:
    """Return the YAML inline representation of a scalar string value.

    Strings that look like integers (e.g. SVN revision ``'176'``) are quoted
    so that YAML round-trips them back as strings.
    """
    dumped: str = yaml.dump(value, default_flow_style=None, allow_unicode=True)
    return dumped.splitlines()[0]


def _line_eol(line: str) -> str:
    """Return the line-ending sequence of *line*, or ``""`` if it has none."""
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def _detect_eol(block: Sequence[str]) -> str:
    r"""Return the line-ending style used in *block*, defaulting to ``\\n``."""
    for line in block:
        eol = _line_eol(line)
        if eol:
            return eol
    return "\n"


def find_field(
    block: Sequence[str],
    field_name: str,
    indent: int,
    start: int = 0,
    end: int | None = None,
) -> int | None:
    """Return the index in *block* of ``field_name:`` at exactly *indent* spaces.

    Searches ``block[start:end]``.  Commented-out lines (where the first
    non-whitespace character is ``#``) are skipped and never matched.
    Returns ``None`` when not found.
    """
    bound = end if end is not None else len(block)
    prefix = " " * indent + field_name + ":"
    for i in range(start, bound):
        stripped = block[i].rstrip("\n\r")
        if stripped.lstrip().startswith("#"):
            continue
        if stripped.startswith(prefix) and (
            len(stripped) == len(prefix) or stripped[len(prefix)] in (" ", "\t")
        ):
            return i
    return None


def update_value(
    block: Sequence[str], line_idx: int, field_name: str, yaml_value: str
) -> list[str]:
    """Return a copy of *block* with the value on *line_idx* replaced by *yaml_value*.

    The indentation, line ending (LF or CRLF), and any trailing comment of
    the original line are all preserved so that in-place edits do not destroy
    annotations or alter the file's line-ending convention.
    """
    result = list(block)
    line = result[line_idx]
    indent = len(line) - len(line.lstrip())
    eol = _line_eol(line)
    stripped = line.rstrip("\n\r")
    comment_match = re.search(r"(\s+#.*)$", stripped)
    comment = comment_match.group(1) if comment_match else ""
    result[line_idx] = " " * indent + field_name + ": " + yaml_value + comment + eol
    return result


def append_field(
    block: Sequence[str],
    field_name: str,
    yaml_value: str,
    indent: int,
    after: int,
) -> list[str]:
    """Return a copy of *block* with ``field_name: yaml_value`` inserted at *after*.

    When *yaml_value* is empty the line is written as ``field_name:`` (no
    value), which is the correct YAML form for a mapping key whose children
    follow on subsequent lines.  The line-ending style (LF or CRLF) is inferred
    from the existing lines in *block*.
    """
    result = list(block)
    value_part = ": " + yaml_value if yaml_value else ":"
    eol = _detect_eol(result)
    result.insert(after, " " * indent + field_name + value_part + eol)
    return result


def _mapping_to_dict(node: MappingNode) -> dict[str, Node]:
    """Convert MappingNode to dict of key -> value node."""
    return {k.value: v for k, v in node.value}


def _find_yaml_node(
    root: MappingNode, path: Sequence[str | dict[str, str]]
) -> Node | MappingNode | SequenceNode | ScalarNode | None:
    """Traverse YAML AST using a path and find node."""
    node: Node | MappingNode | SequenceNode | ScalarNode | None = root

    for step in path:
        node = _traverse_step(node, step)
        if node is None:
            return None

    return node


def _traverse_step(
    node: Node | MappingNode | SequenceNode | ScalarNode | None,
    step: str | dict[str, str],
) -> Node | None:
    """Traverse a single path step in the YAML AST."""
    if isinstance(step, str):
        return _lookup_mapping_key(node, step)
    if isinstance(step, dict):
        return _filter_sequence(node, step)

    raise TypeError(f"Unsupported path step: {step}")


def _lookup_mapping_key(node: Node | None, key: str) -> Node | None:
    """Lookup a key in a MappingNode."""
    if not isinstance(node, MappingNode):
        return None
    mapping = _mapping_to_dict(node)
    return mapping.get(key)


def _filter_sequence(node: Node | None, filter_dict: dict[str, str]) -> Node | None:
    """Filter a SequenceNode by a mapping condition."""
    if not isinstance(node, SequenceNode):
        return None

    key, expected = next(iter(filter_dict.items()))

    for item in node.value:
        if not isinstance(item, MappingNode):
            continue

        mapping = _mapping_to_dict(item)
        value_node = mapping.get(key)

        if isinstance(value_node, ScalarNode) and value_node.value == expected:
            return item

    return None


def get_node_location(
    text: str, path: Sequence[str | dict[str, str]]
) -> YamlNodeLocation | None:
    """Return the location of the YAML node at *path* in *text*."""
    root = yaml.compose(text)
    node = _find_yaml_node(root, path)

    if node is None:
        return None

    return YamlNodeLocation(
        start_line=node.start_mark.line,
        start_col=node.start_mark.column,
        end_line=node.end_mark.line,
        end_col=node.end_mark.column,
    )


def remove_field_block(
    lines: Sequence[str], path_to_field: Sequence[str | dict[str, str]]
) -> list[str]:
    """Remove a YAML field and all its children using AST location.

    Args:
        lines: The YAML content as a list of strings.
        path_to_field: YAML path to the field, e.g. ("manifest", "projects", {"name": "my-project"}, "integrity")

    Returns:
        A new list of lines with the field block removed.
    """
    text = "\n".join(lines)
    loc = get_node_location(text, path_to_field)
    if loc is None:
        # field not found, return original
        return list(lines)

    # remove the lines corresponding to this field
    result = list(lines)
    # AST end_line is inclusive, so make it exclusive
    del result[loc.start_line : loc.end_line + 1]
    return result
