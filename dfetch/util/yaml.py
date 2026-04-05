"""YAML document editor with format-preserving in-place field edits.

Stores a document as raw text lines so that all edits preserve comments,
blank lines, and the original indentation.  A subset of JSONPath (RFC 9535)
addresses fields:

* ``$.key.subkey``                — child member access
* ``$.key[n]``                    — array element by index
* ``[?(@.field == "value")]``     — equality filter on a sequence item

Example::

    doc = YamlDocument(open("config.yaml").read())
    doc.set('$.servers[?(@.name == "primary")]', "port", "8080")
    doc.delete('$.servers[?(@.name == "primary")]', "legacy_key")
    open("config.yaml", "w").write(doc.dump())

The indent step (spaces per nesting level) is inferred automatically from the
document, so 2-space, 4-space, and any other consistent width work correctly.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


@dataclass
class FieldLocation:
    """Source position of a YAML field (0-based line and column)."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass
class NodeMatch:
    """A scalar value matched by a JSONPath query.

    ``value`` is the plain string value (inline comments are stripped by the
    YAML parser).  ``location`` gives the exact source position, useful for
    diagnostics or follow-up edits.
    """

    value: str
    location: FieldLocation


@dataclass
class _FilterStep:
    """An equality-filter step: ``[?(@.key == "value")]``."""

    key: str
    value: str


class YamlDocument:
    """A YAML document that supports format-preserving, JSONPath-driven edits.

    Edits are performed directly on the stored text lines so that comments,
    blank lines, and indentation are never disturbed.
    """

    _MEMBER_RE = re.compile(r"\.([A-Za-z_][A-Za-z0-9_-]*)")
    _INDEX_RE = re.compile(r"\[(\d+)\]")
    _FILTER_RE = re.compile(
        r"""\[\?\(@\.([A-Za-z_][A-Za-z0-9_-]*)\s*==\s*["']([^"']*)["']\s*\)\]"""
    )

    def __init__(self, text: str) -> None:
        """Initialize the document from *text* and analyze its formatting."""
        self.lines: list[str] = text.splitlines(keepends=True)
        self.eol: str = self._detect_eol(self.lines)
        self._indent_step: int = self._detect_indent_step(self.lines)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, jsonpath: str) -> list[NodeMatch]:
        """Return all scalar nodes matching *jsonpath*.

        Addressing a non-scalar (mapping or sequence) node returns an empty
        list; navigate to a scalar leaf first.

        Example::

            matches = doc.get('$.servers[?(@.name == "primary")].port')
        """
        root = yaml.compose("".join(self.lines))
        return self._eval_steps(root, self._parse_jsonpath(jsonpath))

    def set(self, jsonpath: str, field: str, value: str) -> None:
        """Set *field* to *value* for every node matched by *jsonpath*.

        *field* supports dot-notation for nested keys (e.g. ``"outer.inner"``).
        Creates the field if absent; no-op when *jsonpath* matches nothing.

        Example::

            doc.set('$.servers[?(@.name == "primary")]', "port", "8080")
        """
        for parts in self._target_paths(
            self._parse_jsonpath(jsonpath), field.split(".")
        ):
            self._set_by_parts(parts, value)

    def delete(self, jsonpath: str, field: str) -> None:
        """Remove *field* from every node matched by *jsonpath*.

        The field and all its child lines are removed; no-op when absent.
        Deletions are applied in reverse document order so that earlier line
        indices remain valid throughout.

        Example::

            doc.delete('$.servers[?(@.name == "primary")]', "legacy_key")
        """
        targets = self._target_paths(self._parse_jsonpath(jsonpath), [field])
        for parts in reversed(targets):
            self._delete_by_parts(parts)

    def dump(self) -> str:
        """Return the current document as a string."""
        return "".join(self.lines)

    # ------------------------------------------------------------------
    # JSONPath parsing and target resolution
    # ------------------------------------------------------------------

    @classmethod
    def _parse_jsonpath(cls, jsonpath: str) -> list[str | _FilterStep]:
        """Parse *jsonpath* into a list of steps.

        Each step is either a ``str`` (member name or array index) or a
        :class:`_FilterStep`.  Raises :exc:`ValueError` for unsupported syntax.
        """
        path = jsonpath.strip()
        if not path.startswith("$"):
            raise ValueError(f"JSONPath must start with '$': {jsonpath!r}")
        path = path[1:]
        steps: list[str | _FilterStep] = []
        while path:
            if m := cls._FILTER_RE.match(path):
                steps.append(_FilterStep(key=m.group(1), value=m.group(2)))
                path = path[m.end() :]
                continue
            if m := cls._MEMBER_RE.match(path):
                steps.append(m.group(1))
                path = path[m.end() :]
                continue
            if m := cls._INDEX_RE.match(path):
                steps.append(m.group(1))
                path = path[m.end() :]
                continue
            raise ValueError(f"Unsupported JSONPath segment: {path!r}")
        return steps

    def _target_paths(
        self, steps: list[str | _FilterStep], tail: list[str]
    ) -> list[list[str]]:
        """Resolve *steps* + *tail* to concrete text-level part lists.

        When the path contains no filter, returns a single-element list with
        the plain string parts.  With a filter, each matching sequence item
        expands to one entry in document order.
        """
        for i, step in enumerate(steps):
            if isinstance(step, _FilterStep):
                return self._filtered_paths(
                    self._str_steps(steps, end=i),
                    step,
                    self._str_steps(steps, start=i + 1),
                    tail,
                )
        return [self._str_steps(steps) + tail]

    def _filtered_paths(
        self,
        seq_parts: list[str],
        filter_step: _FilterStep,
        post_parts: list[str],
        tail: list[str],
    ) -> list[list[str]]:
        """Return paths for all sequence items matched by *filter_step*."""
        root = yaml.compose("".join(self.lines))
        seq_node = self._traverse_path(root, seq_parts)
        if not isinstance(seq_node, SequenceNode):
            return []
        targets: list[list[str]] = []
        for i, item in enumerate(seq_node.value):
            if not isinstance(item, MappingNode):
                continue
            filter_node = self._mapping_to_dict(item).get(filter_step.key)
            if (
                isinstance(filter_node, ScalarNode)
                and str(filter_node.value) == filter_step.value
            ):
                targets.append(seq_parts + [str(i)] + post_parts + tail)
        return targets

    @staticmethod
    def _str_steps(
        steps: list[str | _FilterStep],
        *,
        start: int = 0,
        end: int | None = None,
    ) -> list[str]:
        """Return only the string steps from *steps[start:end]*."""
        return [s for s in steps[start:end] if isinstance(s, str)]

    # ------------------------------------------------------------------
    # JSONPath AST evaluation (used by get())
    # ------------------------------------------------------------------

    def _eval_steps(
        self, node: Node | None, steps: list[str | _FilterStep]
    ) -> list[NodeMatch]:
        """Recursively evaluate *steps* against YAML AST *node*."""
        if not steps:
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
            return self._eval_str_step(node, step, rest)
        return self._eval_filter_step(node, step, rest)

    def _eval_str_step(
        self, node: Node | None, step: str, rest: list[str | _FilterStep]
    ) -> list[NodeMatch]:
        """Evaluate a member-access or numeric-index step."""
        if isinstance(node, MappingNode):
            return self._eval_steps(self._mapping_to_dict(node).get(step), rest)
        if isinstance(node, SequenceNode) and step.isdigit():
            i = int(step)
            child = node.value[i] if i < len(node.value) else None
            return self._eval_steps(child, rest)
        return []

    def _eval_filter_step(
        self, node: Node | None, step: _FilterStep, rest: list[str | _FilterStep]
    ) -> list[NodeMatch]:
        """Fan out over all sequence items matching *step*."""
        if not isinstance(node, SequenceNode):
            return []
        results: list[NodeMatch] = []
        for item in node.value:
            if not isinstance(item, MappingNode):
                continue
            filter_node = self._mapping_to_dict(item).get(step.key)
            if (
                isinstance(filter_node, ScalarNode)
                and str(filter_node.value) == step.value
            ):
                results.extend(self._eval_steps(item, rest))
        return results

    # ------------------------------------------------------------------
    # Text-level field mutation
    # ------------------------------------------------------------------

    def _set_by_parts(self, parts: list[str], value: str) -> None:
        """Locate the field at *parts* and update it, or insert it if absent."""
        idx = self._find_field(parts)
        if idx is not None:
            self._update_line(idx, parts[-1], value)
        else:
            self._add_field(parts, value)

    def _delete_by_parts(self, parts: list[str]) -> None:
        """Remove the field at *parts* and all of its child lines.

        Stops at the first blank line so the surrounding layout is preserved.
        """
        idx = self._find_field(parts)
        if idx is None:
            return
        field_indent = len(self.lines[idx]) - len(self.lines[idx].lstrip())
        end = idx + 1
        while end < len(self.lines):
            stripped = self.lines[end].rstrip("\n\r")
            if not stripped:
                break
            if stripped.lstrip().startswith("#"):
                end += 1
                continue
            if len(stripped) - len(stripped.lstrip()) <= field_indent:
                break
            end += 1
        del self.lines[idx:end]

    def _update_line(self, idx: int, field_name: str, value: str) -> None:
        """Rewrite line *idx* in-place, preserving any trailing inline comment."""
        line = self.lines[idx]
        indent = len(line) - len(line.lstrip())
        m = re.search(r"(\s+#.*)$", line.rstrip("\n\r"))
        comment = m.group(1) if m else ""
        self.lines[idx] = (
            f"{' ' * indent}{field_name}: {self._yaml_scalar(value)}{comment}{self.eol}"
        )

    def _add_field(self, parts: list[str], value: str, *, at_end: bool = False) -> None:
        """Insert a new ``key: value`` line at the position given by *parts*."""
        parent_parts = parts[:-1]
        field_name = parts[-1]
        parent_idx = self._resolve_parent_idx(parent_parts)
        indent = self._child_indent(parent_idx)
        value_str = f": {self._yaml_scalar(value)}" if value else ":"
        insert_at = self._insert_idx(parent_parts, parent_idx, at_end)
        self.lines.insert(insert_at, f"{' ' * indent}{field_name}{value_str}{self.eol}")

    # ------------------------------------------------------------------
    # Text-level field location
    # ------------------------------------------------------------------

    def _find_field(self, parts: list[str]) -> int | None:
        """Return the line index of the field addressed by *parts*, or ``None``.

        Each part is a mapping key name or a decimal sequence index.  Searches
        are scoped to each matched node's block so a missing field is never
        accidentally matched in a sibling node.

        Both standard (items indented deeper than the parent key) and compact
        (items at the same column as the parent key) YAML sequence styles are
        supported.
        """
        indent = 0
        start = 0
        end = len(self.lines)
        idx: int | None = None
        for key in parts:
            if key.isdigit():
                result = self._find_seq_item(int(key), indent, start, end)
                if result is None:
                    return None
                idx, start, end, indent = result
            else:
                idx = self._find_field_at_indent(key, indent, start, end)
                if idx is None:
                    return None
                # Compact sequence: same-indent '-' lines are children of this
                # key, not block terminators, so pass allow_compact_sequence.
                end = self._block_end(idx, indent, allow_compact_sequence=True)
                start = idx + 1
                indent += self._indent_step
        return idx

    def _find_seq_item(
        self, n: int, indent: int, start: int, end: int
    ) -> tuple[int, int, int, int] | None:
        """Return ``(idx, next_start, block_end, child_indent)`` for the *n*-th item.

        Returns ``None`` when fewer than *n + 1* items exist in ``[start, end)``.
        """
        seq_indent = self._resolve_seq_indent(indent, start, end)
        cur_start = start
        for _ in range(n):
            found = self._find_field_at_indent("-", seq_indent, cur_start, end)
            if found is None:
                return None
            cur_start = found + 1
        idx = self._find_field_at_indent("-", seq_indent, cur_start, end)
        if idx is None:
            return None
        # The "- " block-sequence indicator is always 2 chars wide, so children
        # sit at seq_indent + 2 regardless of the document's overall indent step.
        return idx, idx + 1, self._block_end(idx, seq_indent), seq_indent + 2

    def _resolve_seq_indent(self, indent: int, start: int, end: int) -> int:
        """Return the actual indent at which sequence items appear.

        Tries *indent* first (standard style: items are deeper than the parent
        key).  Falls back to *indent - step* to handle compact sequences where
        items sit at the same column as the parent mapping key.
        """
        if self._find_field_at_indent("-", indent, start, end) is not None:
            return indent
        if indent >= self._indent_step:
            compact = indent - self._indent_step
            if self._find_field_at_indent("-", compact, start, end) is not None:
                return compact
        return indent

    def _find_field_at_indent(
        self, field_name: str, indent: int, start: int, end: int | None = None
    ) -> int | None:
        """Return the first line in ``[start, end)`` that has *field_name* at *indent*."""
        stop = len(self.lines) if end is None else end
        prefix = " " * indent + ("-" if field_name == "-" else f"{field_name}:")
        for i in range(start, stop):
            line = self.lines[i].rstrip("\n\r")
            if line.lstrip().startswith("#"):
                continue
            if line.startswith(prefix) and (
                len(line) == len(prefix) or line[len(prefix)] in (" ", "\t")
            ):
                return i
        return None

    def _block_end(
        self,
        from_idx: int,
        parent_indent: int,
        *,
        allow_compact_sequence: bool = False,
    ) -> int:
        """Return the index of the first line that terminates the block at *from_idx*.

        A line terminates the block when its indentation is ≤ *parent_indent*,
        unless *allow_compact_sequence* is ``True`` and the line is a ``-`` item
        at exactly *parent_indent* — those are children of the current key in
        compact sequence style.  Blank and comment lines are skipped.
        Falls back to ``len(self.lines)`` when no terminator is found.
        """
        for j in range(from_idx + 1, len(self.lines)):
            stripped = self.lines[j].rstrip("\n\r")
            if not stripped or stripped.lstrip().startswith("#"):
                continue
            item_indent = len(stripped) - len(stripped.lstrip())
            if item_indent > parent_indent:
                continue
            if (
                allow_compact_sequence
                and item_indent == parent_indent
                and stripped.lstrip().startswith("-")
            ):
                continue
            return j
        return len(self.lines)

    # ------------------------------------------------------------------
    # Field insertion helpers
    # ------------------------------------------------------------------

    def _resolve_parent_idx(self, parent_parts: list[str]) -> int | None:
        """Return the line index of the parent node, creating it when absent."""
        if not parent_parts:
            return None
        idx = self._find_field(parent_parts)
        if idx is None:
            self._add_field(parent_parts, "", at_end=True)
            idx = self._find_field(parent_parts)
        return idx

    def _child_indent(self, parent_idx: int | None) -> int:
        """Return the column at which a child of *parent_idx* should be written.

        Sequence items use a 2-char ``- `` indicator, so their children sit at
        ``item_indent + 2``.  Mapping keys use the document's indent step.
        """
        if parent_idx is None:
            return 0
        line = self.lines[parent_idx]
        parent_indent = len(line) - len(line.lstrip())
        if line.lstrip().startswith("-"):
            return parent_indent + 2  # "- " indicator is always 2 chars wide
        return parent_indent + self._indent_step

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

    # ------------------------------------------------------------------
    # YAML AST helpers
    # ------------------------------------------------------------------

    def _ast_node_location(self, parts: list[str]) -> FieldLocation | None:
        """Return the source span of the AST node at *parts*, or ``None``."""
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
        """Walk the YAML AST along *path*, returning the terminal node or ``None``."""
        for step in path:
            if node is None:
                return None
            if isinstance(node, MappingNode):
                node = self._mapping_to_dict(node).get(step)
            elif isinstance(node, SequenceNode):
                if step.isdigit():
                    i = int(step)
                    node = node.value[i] if i < len(node.value) else None
                else:
                    node = None
            else:
                return None
        return node

    @staticmethod
    def _mapping_to_dict(node: MappingNode) -> dict[str, Node]:
        return {k.value: v for k, v in node.value}

    # ------------------------------------------------------------------
    # Document-level utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_eol(lines: Sequence[str]) -> str:
        r"""Return the line-ending style used in *lines* (``\\r\\n`` or ``\\n``)."""
        for line in lines:
            if line.endswith("\r\n"):
                return "\r\n"
            if line.endswith("\n"):
                return "\n"
        return "\n"

    @staticmethod
    def _detect_indent_step(lines: Sequence[str]) -> int:
        """Return the indent step (spaces per level) inferred from *lines*.

        Uses the indentation of the first non-blank, non-comment line that has
        positive indentation.  Defaults to 2 when no such line is found.
        """
        for line in lines:
            content = line.rstrip("\n\r")
            stripped = content.lstrip()
            if stripped and not stripped.startswith("#"):
                indent = len(content) - len(stripped)
                if indent > 0:
                    return indent
        return 2

    @staticmethod
    def _yaml_scalar(value: str) -> str:
        """Format *value* as a YAML scalar, quoting when necessary."""
        return yaml.dump(
            value, default_flow_style=None, allow_unicode=True
        ).splitlines()[0]
