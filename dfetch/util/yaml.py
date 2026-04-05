"""Generic YAML text-editing utilities.

These helpers operate on plain lists of text lines and know nothing about
dfetch-specific concepts.  They are used by :mod:`dfetch.manifest.manifest`
to edit manifest files in-place while preserving comments and layout.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


@dataclass
class FieldLocation:
    """Represents the position of a YAML field in a document."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass
class FieldPath:
    """Represents a field path in a YAML document."""

    parts: list[str]

    @classmethod
    def from_str(cls, path: str) -> "FieldPath":
        """Parse a dot-separated field path string."""
        return cls(path.split("."))

    def __str__(self) -> str:
        """Return dot-separated path string."""
        return ".".join(self.parts)


@dataclass
class FieldFilter:
    """Represents a simple filter for fields in a YAML sequence."""

    key: str
    value: str


class YamlDocument:
    """A YAML document supporting smart field manipulation with comments, line endings, and filtering."""

    def __init__(self, text: str) -> None:
        """Initialize with YAML text."""
        self.lines: list[str] = text.splitlines(keepends=True)
        self.eol: str = self._detect_eol(self.lines)

    # ---------------- Line-ending helpers ----------------
    @staticmethod
    def _line_eol(line: str) -> str:
        return (
            "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
        )

    def _detect_eol(self, lines: Sequence[str]) -> str:
        for line in lines:
            eol = self._line_eol(line)
            if eol:
                return eol
        return "\n"

    # ---------------- Scalar handling ----------------
    @staticmethod
    def _yaml_scalar(value: str) -> str:
        dumped = yaml.dump(value, default_flow_style=None, allow_unicode=True)
        return dumped.splitlines()[0]

    # ---------------- Public API ----------------
    def get(self, path: str | FieldPath) -> str | None:
        """Get the value of a field by path."""
        path = FieldPath.from_str(path) if isinstance(path, str) else path
        idx = self._find_field(path)
        if idx is None:
            return None
        line = self.lines[idx].rstrip("\n\r")
        value = line.split(":", 1)[1].split("#", 1)[0].strip()
        return value

    def set(self, path: str | FieldPath, value: str, comment: str = "") -> None:
        """Set or create a field at the given path."""
        path = FieldPath.from_str(path) if isinstance(path, str) else path
        idx = self._find_field(path)
        if idx is not None:
            self._update_line(idx, path.parts[-1], value)
        else:
            self._add_field(path, value, comment)

    def delete(self, path: str | FieldPath) -> None:
        """Delete a field and its children."""
        path = FieldPath.from_str(path) if isinstance(path, str) else path
        loc = self._get_node_location(path)
        if loc:
            del self.lines[loc.start_line : loc.end_line + 1]

    def dump(self) -> str:
        """Return the YAML document as a string."""
        return "".join(self.lines)

    def find_by_filter(
        self, sequence_path: str | FieldPath, field_filter: FieldFilter
    ) -> list[FieldPath]:
        """Find all entries in a YAML sequence where a field has a given value.

        Args:
            sequence_path: Path to the sequence node.
            field_filter: Filter key and expected value.

        Returns:
            List of FieldPath pointing to each matching sequence item.
            Example: for "manifest.projects" with filter "name=foo", returns
            [FieldPath(['manifest', 'projects', '0'])] for the first match.
        """
        sequence_path = (
            FieldPath.from_str(sequence_path)
            if isinstance(sequence_path, str)
            else sequence_path
        )
        root = yaml.compose("".join(self.lines))
        sequence_node = self._traverse_path(root, sequence_path.parts)

        if not isinstance(sequence_node, SequenceNode):
            return []

        matches: list[FieldPath] = []
        for idx, item in enumerate(sequence_node.value):
            if not isinstance(item, MappingNode):
                continue
            mapping = self._mapping_to_dict(item)
            value_node = mapping.get(field_filter.key)
            if (
                isinstance(value_node, ScalarNode)
                and str(value_node.value) == field_filter.value
            ):
                matches.append(FieldPath(sequence_path.parts + [str(idx)]))

        return matches

    # ---------------- Batch operations using filters ----------------
    def update_filtered(
        self,
        sequence_path: str | FieldPath,
        field_filter: FieldFilter,
        updater: str | Callable[[str], str],
        target_field: str | None = None,
    ) -> None:
        """Update all entries in a sequence that match a filter.

        Args:
            sequence_path: Path to the sequence node.
            field_filter: Filter key/value for selecting entries.
            updater: Either a string (new value) or a callable that transforms the old value.
            target_field: Field to update; if None, updates the filtered field itself.
        """
        matches = self.find_by_filter(sequence_path, field_filter)
        for path in matches:
            field_to_update = target_field if target_field else field_filter.key
            field_path = FieldPath(path.parts + [field_to_update])
            current_value: str = self.get(field_path) or ""
            new_value = updater(current_value) if callable(updater) else updater
            self.set(field_path, new_value)

    def delete_filtered(
        self,
        sequence_path: str | FieldPath,
        field_filter: FieldFilter,
    ) -> None:
        """Delete all entries in a sequence that match a filter.

        Args:
            sequence_path: Path to the sequence node.
            field_filter: Filter key/value for selecting entries.
        """
        matches = self.find_by_filter(sequence_path, field_filter)
        # Delete in reverse to avoid shifting line indices
        for path in reversed(matches):
            self.delete(path)

    # ---------------- Internal helpers ----------------
    def _update_line(self, idx: int, field_name: str, value: str) -> None:
        line = self.lines[idx]
        indent = len(line) - len(line.lstrip())
        comment_match = re.search(r"(\s+#.*)$", line.rstrip("\n\r"))
        comment = comment_match.group(1) if comment_match else ""
        self.lines[idx] = (
            f"{' ' * indent}{field_name}: {self._yaml_scalar(value)}{comment}{self.eol}"
        )

    def _resolve_parent_idx(self, parent_path: FieldPath) -> int | None:
        """Return the line index of the parent node, creating it if absent."""
        if not parent_path.parts:
            return None
        idx = self._find_field(parent_path)
        if idx is None:
            self._add_field(parent_path, "", "", _at_end=True)
            idx = self._find_field(parent_path)
        return idx

    def _child_indent(self, parent_idx: int | None) -> int:
        """Return the indent level for a child of the node at *parent_idx*."""
        if parent_idx is None:
            return 0
        line = self.lines[parent_idx]
        return len(line) - len(line.lstrip()) + 2

    def _insert_idx(
        self, parent_path: FieldPath, parent_idx: int | None, at_end: bool
    ) -> int:
        """Return the line index at which to insert the new field."""
        if parent_idx is None:
            return len(self.lines)
        if at_end:
            loc = self.get_node_location(parent_path)
            if loc is not None and loc.end_line > parent_idx:
                return loc.end_line
        return parent_idx + 1

    def _add_field(
        self, path: FieldPath, value: str, comment: str, *, _at_end: bool = False
    ) -> None:
        parent_path = FieldPath(path.parts[:-1])
        field_name = path.parts[-1]
        parent_idx = self._resolve_parent_idx(parent_path)
        indent = self._child_indent(parent_idx)
        value_part = f": {self._yaml_scalar(value)}" if value else ":"
        comment_part = f"  # {comment}" if comment else ""
        insert_idx = self._insert_idx(parent_path, parent_idx, _at_end)
        self.lines.insert(
            insert_idx,
            f"{' ' * indent}{field_name}{value_part}{comment_part}{self.eol}",
        )

    def _find_field(self, path: FieldPath) -> int | None:
        indent = 0
        start = 0
        idx: int | None = None
        i = 0
        while i < len(path.parts):
            key = path.parts[i]
            if key.isdigit():
                # Skip over the first n items to reach the n-th one (0-based).
                for _ in range(int(key) + 1):
                    idx = self._find_field_at_indent("-", indent, start)
                    if idx is None:
                        return None
                    start = idx + 1
                i += 1
                indent += 2
            else:
                idx = self._find_field_at_indent(key, indent, start)
                if idx is None:
                    return None
                start = idx + 1
                i += 1
                indent += 2
        return idx

    def _find_field_at_indent(
        self, field_name: str, indent: int, start: int
    ) -> int | None:
        if field_name == "-":
            prefix = " " * indent + "-"
        else:
            prefix = " " * indent + field_name + ":"
        for i in range(start, len(self.lines)):
            line = self.lines[i].rstrip("\n\r")
            if line.lstrip().startswith("#"):
                continue
            if line.startswith(prefix) and (
                len(line) == len(prefix) or line[len(prefix)] in (" ", "\t")
            ):
                return i
        return None

    # ---------------- YAML AST helpers ----------------
    def get_node_location(self, path: FieldPath) -> FieldLocation | None:
        """Get the location of a node in the document."""
        root = yaml.compose("".join(self.lines))
        node = self._traverse_path(root, path.parts)
        if node is None:
            return None
        return FieldLocation(
            start_line=node.start_mark.line,
            start_col=node.start_mark.column,
            end_line=node.end_mark.line,
            end_col=node.end_mark.column,
        )

    def _get_node_location(self, path: FieldPath) -> FieldLocation | None:
        """Legacy alias for get_node_location."""
        return self.get_node_location(path)

    def _traverse_path(self, node: Node | None, path: Sequence[str]) -> Node | None:
        for step in path:
            if node is None:
                return None
            if isinstance(node, MappingNode):
                node = self._mapping_to_dict(node).get(step)
            elif isinstance(node, SequenceNode):
                if step.isdigit():
                    idx = int(step)
                    node = node.value[idx] if idx < len(node.value) else None
                else:
                    node = None
            else:
                return None
        return node

    @staticmethod
    def _mapping_to_dict(node: MappingNode) -> dict[str, Node]:
        return {k.value: v for k, v in node.value}
