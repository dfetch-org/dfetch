"""Various patch utilities for VCS systems."""

from __future__ import annotations

import copy
import datetime
import difflib
import hashlib
import re
import stat
from collections.abc import Sequence
from dataclasses import dataclass, field
from email.utils import format_datetime
from enum import Enum
from pathlib import Path

import patch_ng

from dfetch.log import configure_external_logger

configure_external_logger("patch_ng")


class PatchType(Enum):
    """Type of patch."""

    DIFF = patch_ng.DIFF
    GIT = patch_ng.GIT
    HG = patch_ng.HG
    SVN = patch_ng.SVN
    PLAIN = patch_ng.PLAIN
    MIXED = patch_ng.MIXED


@dataclass
class PatchResult:
    """Result of applying a patch."""

    encoding_warning: bool = False


@dataclass(eq=False)
class Patch:
    """Patch object for parsing, manipulating, and applying patches.

    This class provides a high-level interface for working with patches, abstracting
    away the underlying patch_ng library. It supports loading patches from files or
    strings, applying them to a filesystem, and converting between different patch
    formats (e.g., git vs svn). It also allows for filtering out specific files and
    adding path prefixes to all files in the patch. The class is designed to be flexible
    and extensible, making it easier to work with patches in various contexts.
    """

    _patchset: patch_ng.PatchSet
    path: str = ""
    _result: PatchResult = field(default_factory=PatchResult)

    @staticmethod
    def from_file(path: str | Path) -> Patch:
        """Create patch object from file."""
        ps = patch_ng.fromfile(str(path))
        result = PatchResult()

        if not ps:
            with open(path, "rb") as patch_file:
                patch_text = patch_ng.decode_text(patch_file.read()).encode("utf-8")
                ps = patch_ng.fromstring(patch_text)

                if ps:
                    result.encoding_warning = True

        if not ps or not ps.items:
            raise RuntimeError(f'Invalid or empty patch: "{path}"')
        return Patch(ps, path=str(path), _result=result)

    @staticmethod
    def from_bytes(data: bytes) -> Patch:
        """Create patch object from data bytes."""
        ps = patch_ng.fromstring(data)
        if not ps or not ps.items:
            raise RuntimeError("Invalid patch input")
        return Patch(ps)

    @staticmethod
    def from_string(data: str) -> Patch:
        """Create patch object from str."""
        return Patch.from_bytes(data.encode("UTF-8"))

    @staticmethod
    def _unified_diff_new_file(path: Path) -> list[str]:
        """Create a unified diff for a new file."""
        with path.open("r", encoding="utf-8", errors="replace") as new_file:
            lines = new_file.readlines()

        return list(
            difflib.unified_diff(
                [], lines, fromfile="/dev/null", tofile=str(path), lineterm="\n"
            )
        )

    @staticmethod
    def _for_new_file(file_path: str | Path, patch_type: PatchType) -> Patch:
        """Create a patch for a new untracked file, preserving file mode."""
        path = Path(file_path)
        diff = Patch._unified_diff_new_file(path)

        if not diff:
            return Patch.empty().convert_type(patch_type)

        if patch_type == PatchType.GIT:
            return Patch.from_string(
                "".join(
                    [
                        f"diff --git a/{file_path} b/{file_path}\n",
                        f"new file mode {_git_mode(path)}\n",
                        f"index 0000000..{_git_blob_sha1(path)[:7]}\n",
                    ]
                    + diff
                )
            )

        if patch_type == PatchType.SVN:
            return Patch.from_string(
                "".join([f"Index: {file_path}\n", "=" * 67 + "\n"] + diff)
            )
        return Patch.from_string("".join(diff))

    @staticmethod
    def for_new_files(
        file_paths: list[str] | list[Path], patch_type: PatchType
    ) -> Patch:
        """Create a patch for multiple new files."""
        patch: Patch | None = None
        for file in file_paths:
            new_patch = Patch._for_new_file(file, patch_type)
            if not new_patch.is_empty():
                if patch is None:
                    patch = new_patch
                else:
                    patch.extend(new_patch)

        return patch if patch is not None else Patch.empty()

    @staticmethod
    def empty() -> Patch:
        """Create empty patch object."""
        return Patch(patch_ng.PatchSet())

    def is_empty(self) -> bool:
        """Check if the patch is empty."""
        return not self._patchset.items

    @property
    def files(self) -> list[str]:
        """Get a list of all target files."""
        return [patch.target.decode("utf-8") for patch in self._patchset.items]

    def apply(self, root: str = ".", fuzz: bool = True) -> PatchResult:
        """Apply this patch to a filesystem root."""
        if not self._patchset.apply(strip=0, root=root, fuzz=fuzz):
            raise RuntimeError(
                f'Applying patch "{self.path or "<inline patch>"}" failed'
            )

        return self._result

    def dump(self) -> str:
        """Serialize patch back to unified diff text."""
        if self.is_empty():
            return ""

        patch_lines: list[str] = []

        for p in self._patchset.items:
            for headline in p.header:
                patch_lines.append(headline.rstrip(b"\r\n").decode("utf-8"))

            source, target = p.source.decode("utf-8"), p.target.decode("utf-8")
            if p.type == patch_ng.GIT:
                if source != "/dev/null":
                    source = "a/" + source
                if target != "/dev/null":
                    target = "b/" + target

            patch_lines.append(f"--- {source}")
            patch_lines.append(f"+++ {target}")
            for h in p.hunks:
                patch_lines.append(
                    f"@@ -{h.startsrc},{h.linessrc} +{h.starttgt},{h.linestgt} @@"
                )
                for line in h.text:
                    patch_lines.append(line.rstrip(b"\r\n").decode("utf-8"))
        return "\n".join(patch_lines) + "\n" if patch_lines else ""

    def dump_header(self, patch_info: PatchInfo) -> str:
        """Dump patch header based on patch type."""
        if self._patchset.type == PatchType.GIT.value:
            return patch_info.to_git_header()
        return ""

    def reverse(self) -> Patch:
        """Reverse this patch."""
        if self.is_empty():
            return self
        reversed_text = _reverse_patch(self.dump())
        if not reversed_text:
            raise RuntimeError("Failed to reverse patch")
        self._patchset = self.from_bytes(  # pylint: disable=protected-access
            reversed_text.encode("utf-8")
        )._patchset
        return self

    def filter(self, ignore: Sequence[str]) -> Patch:
        """Remove the ignored files."""
        filtered = patch_ng.PatchSet()
        filtered.type = self._patchset.type
        for p in self._patchset:
            if p.target.decode("utf-8") not in ignore:
                filtered.items.append(p)
        self._patchset = filtered
        return self

    def add_prefix(self, path_prefix: str) -> Patch:
        """Add path_prefix to all file paths."""
        prefix = path_prefix.strip("/").encode()
        if prefix:
            prefix += b"/"

        diff_git = re.compile(
            r"^diff --git (?:(?P<a>a/))?(?P<old>.+) (?:(?P<b>b/))?(?P<new>.+?)[\r\n]*$"
        )
        svn_index = re.compile(rb"^Index: (?P<target>.+)$")

        for file in self._patchset.items:
            file.source = _rewrite_path(prefix, file.source)
            file.target = _rewrite_path(prefix, file.target)

            for idx, line in enumerate(file.header):

                git_match = diff_git.match(line.decode("utf-8", errors="replace"))
                if git_match:
                    file.header[idx] = (
                        b"diff --git "
                        + (
                            git_match.group("a").encode()
                            if git_match.group("a")
                            else b""
                        )
                        + _rewrite_path(prefix, git_match.group("old").encode())
                        + b" "
                        + (
                            git_match.group("b").encode()
                            if git_match.group("b")
                            else b""
                        )
                        + _rewrite_path(prefix, git_match.group("new").encode())
                    )
                    break

                svn_match = svn_index.match(line)
                if svn_match:
                    file.header[idx] = b"Index: " + _rewrite_path(
                        prefix, svn_match.group("target")
                    )
                    break

        return self

    def convert_type(self, required: PatchType) -> Patch:
        """Convert patch type: patch_ng.GIT <-> patch_ng.SVN. No-op for other types."""
        if required.value == self._patchset.type:
            return self

        if required.value == patch_ng.GIT:
            for file in self._patchset.items:
                file.header = [
                    b"diff --git "
                    + _rewrite_path(b"a/", file.source)
                    + b" "
                    + _rewrite_path(b"b/", file.target)
                    + b"\n"
                ]
                file.type = required.value
        elif required.value == patch_ng.SVN:
            for file in self._patchset.items:
                file.header = [b"Index: " + file.target + b"\n", b"=" * 67 + b"\n"]
                file.type = required.value
        else:
            # Unsupported conversion, leave headers and per-file types unchanged.
            return self
        self._patchset.type = required.value
        return self

    def extend(self, other: Patch | Sequence[Patch]) -> Patch:
        """Extend this patch with another patch or sequence of patches."""
        if isinstance(other, Patch):
            other = [other]

        for patch in other:
            if (
                patch._patchset.type  # pylint: disable=protected-access
                != self._patchset.type
            ):
                patch = copy.deepcopy(patch)
                patch.convert_type(PatchType(self._patchset.type))

            self._patchset.items += copy.copy(
                patch._patchset.items  # pylint: disable=protected-access
            )

        return self


def _git_mode(path: Path) -> str:
    if path.is_symlink():
        return "120000"
    perms = stat.S_IMODE(path.stat().st_mode)
    return "100755" if perms & stat.S_IXUSR else "100644"


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    store = header + data
    return hashlib.sha1(store, usedforsecurity=False).hexdigest()


def _reverse_patch(patch_text: str) -> str:
    """Reverse the given patch."""
    patch = patch_ng.fromstring(patch_text.encode("utf-8"))

    reverse_patch_lines: list[bytes] = []

    if not patch:
        return ""

    for file in patch.items:
        reverse_patch_lines.extend(line.rstrip(b"\r\n") for line in file.header)
        reverse_patch_lines.append(b"--- " + file.target)
        reverse_patch_lines.append(b"+++ " + file.source)
        for hunk in file.hunks:
            # swap additions and deletions in the hunk
            hunk_lines: list[bytes] = []
            additions: list[bytes] = []
            deletions: list[bytes] = []

            for line in hunk.text:
                line = line.rstrip(b"\r\n")
                if line.startswith(b"+"):
                    additions.append(b"-" + line[1:])
                elif line.startswith(b"-"):
                    deletions.append(b"+" + line[1:])
                else:
                    # flush accumulated lines before normal line
                    hunk_lines.extend(additions)
                    hunk_lines.extend(deletions)
                    deletions.clear()
                    additions.clear()
                    hunk_lines.append(line)

            # flush leftovers at end
            hunk_lines.extend(additions)
            hunk_lines.extend(deletions)

            # Rebuild hunk header
            reverse_patch_lines.append(
                f"@@ -{hunk.starttgt},{hunk.linestgt} +{hunk.startsrc},{hunk.linessrc} @@".encode(
                    encoding="UTF-8"
                )
            )
            reverse_patch_lines.extend(hunk_lines)
        reverse_patch_lines.append(b"")  # blank line between files

    return (b"\n".join(reverse_patch_lines)).decode(encoding="UTF-8")


@dataclass
class PatchAuthor:
    """Information about a patch author."""

    name: str
    email: str


@dataclass
class PatchInfo:
    """Information about a patch file."""

    author: PatchAuthor
    subject: str
    total_patches: int = 1
    current_patch_idx: int = 1
    revision: str = ""
    date: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
    )
    description: str = ""

    def to_git_header(self) -> str:
        """Convert patch info to a string."""
        subject_line = (
            f"[PATCH {self.current_patch_idx}/{self.total_patches}] {self.subject}"
            if self.total_patches > 1
            else f"[PATCH] {self.subject}"
        )
        return (
            f"From {self.revision or '0000000000000000000000000000000000000000'} Mon Sep 17 00:00:00 2001\n"
            f"From: {self.author.name} <{self.author.email}>\n"
            f"Date: {format_datetime(self.date)}\n"
            f"Subject: {subject_line}\n"
            "\n"
            f"{self.description if self.description else self.subject}\n"
            "\n"
        )


def _rewrite_path(prefix: bytes, path: bytes) -> bytes:
    """Add prefix if a real path."""
    if path == b"/dev/null":
        return b"/dev/null"
    return prefix + path
