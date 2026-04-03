"""Generic YAML text-editing utilities.

These helpers operate on plain lists of text lines and know nothing about
dfetch-specific concepts.  They are used by :mod:`dfetch.manifest.manifest`
to edit manifest files in-place while preserving comments and layout.
"""

import re

import yaml


def yaml_scalar(value: str) -> str:
    """Return the YAML inline representation of a scalar string value.

    Strings that look like integers (e.g. SVN revision ``'176'``) are quoted
    so that YAML round-trips them back as strings.
    """
    dumped: str = yaml.dump(value, default_flow_style=None, allow_unicode=True)
    return dumped.splitlines()[0]


def find_field(
    block: list[str],
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


def _detect_eol(block: list[str]) -> str:
    """Return the line-ending style used in *block*, defaulting to ``\\n``."""
    for line in block:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def update_value(
    block: list[str], line_idx: int, field_name: str, yaml_value: str
) -> list[str]:
    """Return a copy of *block* with the value on *line_idx* replaced by *yaml_value*.

    The indentation, line ending (LF or CRLF), and any trailing comment of
    the original line are all preserved so that in-place edits do not destroy
    annotations or alter the file's line-ending convention.
    """
    block = list(block)
    line = block[line_idx]
    indent = len(line) - len(line.lstrip())
    eol = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    stripped = line.rstrip("\n\r")
    comment_match = re.search(r"(\s+#.*)$", stripped)
    comment = comment_match.group(1) if comment_match else ""
    block[line_idx] = " " * indent + field_name + ": " + yaml_value + comment + eol
    return block


def append_field(
    block: list[str],
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
    block = list(block)
    value_part = ": " + yaml_value if yaml_value else ":"
    eol = _detect_eol(block)
    block.insert(after, " " * indent + field_name + value_part + eol)
    return block
