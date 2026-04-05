"""Generic YAML text-editing utilities.

These helpers operate on plain lists of text lines and know nothing about
dfetch-specific concepts.  They are used by :mod:`dfetch.manifest.manifest`
to edit manifest files in-place while preserving comments and layout.

The public interface uses a subset of JSONPath (RFC 9535) to address fields:

* ``$.key.subkey``                     — child member access
* ``$.key[n]``                         — array element by index
* ``[?(@.field == "value")]``          — filter (string equality only)

Combining these, the typical freeze call looks like::

    doc.set(
        '$.manifest.projects[?(@.name == "my-project")]',
        "tag",
        "v1.2.3",
    )

**Indentation assumption**: dfetch manifests use 2-space indentation.
The text-walking helpers rely on this and will not work correctly for
other indentation widths.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


@dataclass
class FieldLocation:
    """Position of a YAML field in a document (0-based line and column)."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass
class NodeMatch:
    """A scalar value in the document matched by a JSONPath expression.

    ``value`` is the plain string value; ``location`` is its exact source
    position, suitable for SARIF diagnostics or follow-up edits.
    """

    value: str
    location: FieldLocation


@dataclass
class _FilterStep:
    """An equality-filter step: ``[?(@.key == "value")]``."""

    key: str
    value: str


class YamlDocument:
    """A YAML document supporting JSONPath-driven, format-preserving field edits.

    The document is stored as a list of raw text lines so that all edits
    preserve comments, blank lines, and the original indentation.
    JSONPath expressions (RFC 9535 subset) are used to locate and mutate
    fields via :meth:`get` and :meth:`set`.
    """

    # ------------------------------------------------------------------ #
    # JSONPath parsing regexes                                             #
    # ------------------------------------------------------------------ #

    _MEMBER_RE = re.compile(r"\.([A-Za-z_][A-Za-z0-9_-]*)")
    _INDEX_RE = re.compile(r"\[(\d+)\]")
    # Matches [?(@.key == "value")] or [?(@.key == 'value')] with optional spaces.
    _FILTER_RE = re.compile(
        r"""\[\?\(@\.([A-Za-z_][A-Za-z0-9_-]*)\s*==\s*["']([^"']*)["']\s*\)\]"""
    )

    def __init__(self, text: str) -> None:
        """Initialise from a YAML string."""
        self.lines: list[str] = text.splitlines(keepends=True)
        self.eol: str = self._detect_eol(self.lines)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def get(self, jsonpath: str) -> list[NodeMatch]:
        """Return all scalar nodes matching *jsonpath*.

        Uses the YAML AST for accurate location tracking.  If the path
        addresses a non-scalar (mapping or sequence) node the result is
        empty — navigate further to a scalar leaf first.

        Note: The YAML parser strips inline comments, so the returned
        ``value`` never contains text after ``#``.  Values that contain
        ``#`` inside YAML quotes will be returned correctly by this method
        (unlike the old text-splitting approach).

        Example::

            matches = doc.get('$.manifest.projects[?(@.name == "foo")].name')
            loc = matches[0].location   # FieldLocation with line/col

        """
        steps = self._parse_jsonpath(jsonpath)
        root = yaml.compose("".join(self.lines))
        return self._eval_steps(root, steps)

    def set(self, jsonpath: str, field: str, value: str) -> None:
        """Set *field* to *value* for every node matched by *jsonpath*.

        *jsonpath* selects the container(s) — typically a sequence item
        matched by a filter expression.  *field* is the key within each
        matched container to create or update, and supports dot-notation
        for nested paths (e.g. ``"integrity.hash"``).

        Example::

            doc.set(
                '$.manifest.projects[?(@.name == "my-project")]',
                "tag",
                "v1.2.3",
            )

        If no node matches *jsonpath* the call is a no-op.
        """
        steps = self._parse_jsonpath(jsonpath)

        filter_idx = next(
            (i for i, s in enumerate(steps) if isinstance(s, _FilterStep)), None
        )

        if filter_idx is None:
            # Simple path — combine steps with field parts and set directly.
            parts = [s for s in steps if isinstance(s, str)] + field.split(".")
            self._set_by_parts(parts, value)
            return

        # There is a filter step: navigate to the sequence via the YAML AST,
        # find matching items by index, then use text-walking to mutate each.
        sequence_parts = [s for s in steps[:filter_idx] if isinstance(s, str)]
        filter_step: _FilterStep = steps[filter_idx]  # type: ignore[assignment]
        # Any path steps after the filter are inserted between the item path and field.
        post_filter_parts = [s for s in steps[filter_idx + 1 :] if isinstance(s, str)]

        root = yaml.compose("".join(self.lines))
        sequence_node = self._traverse_path(root, sequence_parts)
        if not isinstance(sequence_node, SequenceNode):
            return

        for item_idx, item in enumerate(sequence_node.value):
            if not isinstance(item, MappingNode):
                continue
            mapping = self._mapping_to_dict(item)
            filter_node = mapping.get(filter_step.key)
            if not (
                isinstance(filter_node, ScalarNode)
                and str(filter_node.value) == filter_step.value
            ):
                continue
            target_parts = (
                sequence_parts
                + [str(item_idx)]
                + post_filter_parts
                + field.split(".")
            )
            self._set_by_parts(target_parts, value)

    def delete(self, jsonpath: str, field: str) -> None:
        """Remove *field* from every node matched by *jsonpath*.

        *field* may be a simple key (``"revision"``) or a top-level nested
        key (``"integrity"``); all child lines are removed together with the
        key itself.  If the field is absent the call is a no-op.

        Example::

            doc.delete(
                '$.manifest.projects[?(@.name == "my-project")]',
                "revision",
            )
        """
        steps = self._parse_jsonpath(jsonpath)

        filter_idx = next(
            (i for i, s in enumerate(steps) if isinstance(s, _FilterStep)), None
        )

        if filter_idx is None:
            parts = [s for s in steps if isinstance(s, str)] + [field]
            self._delete_by_parts(parts)
            return

        sequence_parts = [s for s in steps[:filter_idx] if isinstance(s, str)]
        filter_step: _FilterStep = steps[filter_idx]  # type: ignore[assignment]
        post_filter_parts = [s for s in steps[filter_idx + 1 :] if isinstance(s, str)]

        root = yaml.compose("".join(self.lines))
        sequence_node = self._traverse_path(root, sequence_parts)
        if not isinstance(sequence_node, SequenceNode):
            return

        # Collect targets first then delete in reverse so earlier deletions
        # don't shift the line indices of later ones.
        targets: list[list[str]] = []
        for item_idx, item in enumerate(sequence_node.value):
            if not isinstance(item, MappingNode):
                continue
            mapping = self._mapping_to_dict(item)
            filter_node = mapping.get(filter_step.key)
            if not (
                isinstance(filter_node, ScalarNode)
                and str(filter_node.value) == filter_step.value
            ):
                continue
            targets.append(
                sequence_parts + [str(item_idx)] + post_filter_parts + [field]
            )

        for parts in reversed(targets):
            self._delete_by_parts(parts)

    def dump(self) -> str:
        """Return the current document as a string."""
        return "".join(self.lines)

    # ------------------------------------------------------------------ #
    # JSONPath parsing                                                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def _parse_jsonpath(cls, jsonpath: str) -> list[str | _FilterStep]:
        """Parse *jsonpath* into a list of steps.

        Each step is either a ``str`` (member name or numeric index) or a
        :class:`_FilterStep`.  Raises :exc:`ValueError` for unsupported syntax.
        """
        path = jsonpath.strip()
        if not path.startswith("$"):
            raise ValueError(f"JSONPath must start with '$': {jsonpath!r}")
        path = path[1:]  # strip leading '$'

        steps: list[str | _FilterStep] = []
        while path:
            # Try filter before member so [?(...)] is not consumed as [ ]
            m = cls._FILTER_RE.match(path)
            if m:
                steps.append(_FilterStep(key=m.group(1), value=m.group(2)))
                path = path[m.end() :]
                continue
            m = cls._MEMBER_RE.match(path)
            if m:
                steps.append(m.group(1))
                path = path[m.end() :]
                continue
            m = cls._INDEX_RE.match(path)
            if m:
                steps.append(m.group(1))  # stored as string digit
                path = path[m.end() :]
                continue
            raise ValueError(f"Unsupported JSONPath segment: {path!r}")
        return steps

    # ------------------------------------------------------------------ #
    # JSONPath evaluation (used by get())                                  #
    # ------------------------------------------------------------------ #

    def _eval_steps(
        self, node: Node | None, steps: list[str | _FilterStep]
    ) -> list[NodeMatch]:
        """Recursively evaluate *steps* against YAML AST *node*."""
        if not steps:
            # Leaf: return a match only for scalar nodes.
            if isinstance(node, ScalarNode):
                return [
                    NodeMatch(
                        value=str(node.value),
                        location=FieldLocation(
                            start_line=node.start_mark.line,
                            start_col=node.start_mark.column,
                            end_line=node.end_mark.line,
                            end_col=node.end_mark.column,
                        ),
                    )
                ]
            return []

        step, *rest = steps

        if isinstance(step, str):
            # Member access or numeric index.
            if isinstance(node, MappingNode):
                child = self._mapping_to_dict(node).get(step)
                return self._eval_steps(child, rest)
            if isinstance(node, SequenceNode) and step.isdigit():
                idx = int(step)
                child = node.value[idx] if idx < len(node.value) else None
                return self._eval_steps(child, rest)
            return []

        # _FilterStep — fan out over all matching sequence items.
        if not isinstance(node, SequenceNode):
            return []
        results: list[NodeMatch] = []
        for item in node.value:
            if not isinstance(item, MappingNode):
                continue
            mapping = self._mapping_to_dict(item)
            filter_node = mapping.get(step.key)
            if (
                isinstance(filter_node, ScalarNode)
                and str(filter_node.value) == step.value
            ):
                results.extend(self._eval_steps(item, rest))
        return results

    # ------------------------------------------------------------------ #
    # Text-level mutation helpers                                          #
    # ------------------------------------------------------------------ #

    def _delete_by_parts(self, parts: list[str]) -> None:
        """Remove the field at *parts* and all of its child lines.

        Blank lines are treated as block separators and are never deleted,
        so the surrounding layout is preserved even when a field is the last
        item inside a sequence element.
        """
        idx = self._find_field(parts)
        if idx is None:
            return
        line = self.lines[idx]
        field_indent = len(line) - len(line.lstrip())
        end_idx = idx + 1
        while end_idx < len(self.lines):
            next_stripped = self.lines[end_idx].rstrip("\n\r")
            if not next_stripped:
                break  # blank line ends this field's block
            if next_stripped.lstrip().startswith("#"):
                end_idx += 1
                continue
            if len(next_stripped) - len(next_stripped.lstrip()) <= field_indent:
                break
            end_idx += 1
        del self.lines[idx:end_idx]

    def _set_by_parts(self, parts: list[str], value: str) -> None:
        """Locate the field at *parts* and update it, or add it if absent."""
        idx = self._find_field(parts)
        if idx is not None:
            self._update_line(idx, parts[-1], value)
        else:
            self._add_field(parts, value, "")

    def _update_line(self, idx: int, field_name: str, value: str) -> None:
        line = self.lines[idx]
        indent = len(line) - len(line.lstrip())
        comment_match = re.search(r"(\s+#.*)$", line.rstrip("\n\r"))
        comment = comment_match.group(1) if comment_match else ""
        self.lines[idx] = (
            f"{' ' * indent}{field_name}: {self._yaml_scalar(value)}{comment}{self.eol}"
        )

    def _resolve_parent_idx(self, parent_parts: list[str]) -> int | None:
        """Return the line index of the parent node, creating it if absent."""
        if not parent_parts:
            return None
        idx = self._find_field(parent_parts)
        if idx is None:
            self._add_field(parent_parts, "", "", _at_end=True)
            idx = self._find_field(parent_parts)
        return idx

    def _child_indent(self, parent_idx: int | None) -> int:
        """Return the indent for a child of the node at *parent_idx*."""
        if parent_idx is None:
            return 0
        line = self.lines[parent_idx]
        return len(line) - len(line.lstrip()) + 2

    def _insert_idx(
        self, parent_parts: list[str], parent_idx: int | None, at_end: bool
    ) -> int:
        """Return the line index at which to insert a new field."""
        if parent_idx is None:
            return len(self.lines)
        if at_end:
            loc = self._ast_node_location(parent_parts)
            if loc is not None and loc.end_line > parent_idx:
                return loc.end_line
        return parent_idx + 1

    def _add_field(
        self, parts: list[str], value: str, comment: str, *, _at_end: bool = False
    ) -> None:
        parent_parts = parts[:-1]
        field_name = parts[-1]
        parent_idx = self._resolve_parent_idx(parent_parts)
        indent = self._child_indent(parent_idx)
        value_part = f": {self._yaml_scalar(value)}" if value else ":"
        comment_part = f"  # {comment}" if comment else ""
        insert_idx = self._insert_idx(parent_parts, parent_idx, _at_end)
        self.lines.insert(
            insert_idx,
            f"{' ' * indent}{field_name}{value_part}{comment_part}{self.eol}",
        )

    def _block_end(self, from_idx: int, parent_indent: int) -> int:
        """Return the first line index after *from_idx* whose indentation is
        no greater than *parent_indent*, skipping blank and comment lines.

        This bounds child-field searches to the node that was just matched,
        preventing a missing field from being found in a sibling node.
        Falls back to ``len(self.lines)`` when no such line exists.
        """
        for j in range(from_idx + 1, len(self.lines)):
            stripped = self.lines[j].rstrip("\n\r")
            if not stripped or stripped.lstrip().startswith("#"):
                continue  # blank / comment lines do not end a block
            if len(stripped) - len(stripped.lstrip()) <= parent_indent:
                return j
        return len(self.lines)

    def _find_field(self, parts: list[str]) -> int | None:
        # Dfetch manifests always use 2-space indentation.  Each path segment
        # moves one level deeper, so the expected indent increases by 2 per
        # step.  _find_field_at_indent matches lines that start with exactly
        # ``indent`` spaces followed by the field name (or "-" for list items).
        # Searches are bounded to the matched node's block (via _block_end) so
        # a missing field is not wrongly found inside a later sibling.
        # This will not work correctly for manifests with other indentation widths.
        indent = 0
        start = 0
        end = len(self.lines)
        idx: int | None = None
        i = 0
        while i < len(parts):
            key = parts[i]
            if key.isdigit():
                # Skip to the n-th sequence item (0-based).
                for _ in range(int(key) + 1):
                    idx = self._find_field_at_indent("-", indent, start, end)
                    if idx is None:
                        return None
                    start = idx + 1
                # Bound child searches to this item's block.
                assert idx is not None  # guaranteed by the return None guard above
                end = self._block_end(idx, indent)
                i += 1
                indent += 2
            else:
                idx = self._find_field_at_indent(key, indent, start, end)
                if idx is None:
                    return None
                # Bound child searches to this key's block.
                end = self._block_end(idx, indent)
                start = idx + 1
                i += 1
                indent += 2
        return idx

    def _find_field_at_indent(
        self, field_name: str, indent: int, start: int, end: int | None = None
    ) -> int | None:
        stop = end if end is not None else len(self.lines)
        if field_name == "-":
            prefix = " " * indent + "-"
        else:
            prefix = " " * indent + field_name + ":"
        for i in range(start, stop):
            line = self.lines[i].rstrip("\n\r")
            if line.lstrip().startswith("#"):
                continue
            if line.startswith(prefix) and (
                len(line) == len(prefix) or line[len(prefix)] in (" ", "\t")
            ):
                return i
        return None

    # ------------------------------------------------------------------ #
    # YAML AST helpers                                                     #
    # ------------------------------------------------------------------ #

    def _ast_node_location(self, parts: list[str]) -> FieldLocation | None:
        """Return the source location of the AST node at *parts*, or None."""
        root = yaml.compose("".join(self.lines))
        node = self._traverse_path(root, parts)
        if node is None:
            return None
        return FieldLocation(
            start_line=node.start_mark.line,
            start_col=node.start_mark.column,
            end_line=node.end_mark.line,
            end_col=node.end_mark.column,
        )

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

    # ------------------------------------------------------------------ #
    # Line-ending helpers                                                  #
    # ------------------------------------------------------------------ #

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

    @staticmethod
    def _yaml_scalar(value: str) -> str:
        dumped: str = yaml.dump(value, default_flow_style=None, allow_unicode=True)
        return dumped.splitlines()[0]
