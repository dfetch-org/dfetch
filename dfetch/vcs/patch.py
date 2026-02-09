"""Various patch utilities for VCS systems."""

import datetime
import difflib
import hashlib
import re
import stat
from collections.abc import Sequence
from dataclasses import dataclass, field
from email.utils import format_datetime
from pathlib import Path

import patch_ng

from dfetch.log import configure_external_logger

configure_external_logger("patch_ng")


@dataclass
class PatchResult:
    """Result of applying a patch."""

    encoding_warning: bool = False


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


def filter_patch(patch_text: bytes, ignore: Sequence[str]) -> str:
    """Filter out files from a patch text."""
    if not patch_text:
        return ""

    filtered_patchset = patch_ng.PatchSet()
    unfiltered_patchset = patch_ng.fromstring(patch_text) or []

    for patch in unfiltered_patchset:
        if patch.target.decode("utf-8") not in ignore:
            filtered_patchset.items += [patch]

    return dump_patch(filtered_patchset)


def dump_patch(patch_set: patch_ng.PatchSet) -> str:
    """Dump a patch to string."""
    patch_lines: list[str] = []

    for p in patch_set.items:
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


def apply_patch(
    patch_path: str,
    root: str = ".",
) -> PatchResult:
    """Apply the specified patch relative to the root."""
    patch_set = patch_ng.fromfile(patch_path)

    result = PatchResult()

    if not patch_set:
        with open(patch_path, "rb") as patch_file:
            patch_text = patch_ng.decode_text(patch_file.read()).encode("utf-8")
            patch_set = patch_ng.fromstring(patch_text)

            if patch_set:
                result.encoding_warning = True

    if not patch_set:
        raise RuntimeError(f'Invalid patch file: "{patch_path}"')
    if not patch_set.apply(strip=0, root=root, fuzz=True):
        raise RuntimeError(f'Applying patch "{patch_path}" failed')

    return result


def create_svn_patch_for_new_file(file_path: str) -> str:
    """Create a svn patch for a new file."""
    diff = _unified_diff_new_file(Path(file_path))
    return (
        "" if not diff else "".join([f"Index: {file_path}\n", "=" * 67 + "\n"] + diff)
    )


def create_git_patch_for_new_file(file_path: str) -> str:
    """Create a Git patch for a new untracked file, preserving file mode."""
    path = Path(file_path)
    diff = _unified_diff_new_file(path)

    return (
        ""
        if not diff
        else "".join(
            [
                f"diff --git a/{file_path} b/{file_path}\n",
                f"new file mode {_git_mode(path)}\n",
                f"index 0000000..{_git_blob_sha1(path)[:7]}\n",
            ]
            + diff
        )
    )


def _unified_diff_new_file(path: Path) -> list[str]:
    """Create a unified diff for a new file."""
    with path.open("r", encoding="utf-8", errors="replace") as new_file:
        lines = new_file.readlines()

    return list(
        difflib.unified_diff(
            [], lines, fromfile="/dev/null", tofile=str(path), lineterm="\n"
        )
    )


def combine_patches(patches: Sequence[bytes]) -> str:
    """Combine multiple patches into a single patch."""
    if not patches:
        return ""

    final_patchset = patch_ng.PatchSet()
    for patch in patches:
        for patch_obj in patch_ng.fromstring(patch) or []:
            final_patchset.items += [patch_obj]

    return dump_patch(final_patchset)


def reverse_patch(patch_text: bytes) -> str:
    """Reverse the given patch."""
    patch = patch_ng.fromstring(patch_text)

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

    def to_svn_header(self) -> str:
        """Convert patch info to a string."""
        return ""


def parse_patch(file_path: str | Path) -> patch_ng.PatchSet:
    """Parse the patch from file_path."""
    patch = patch_ng.fromfile(str(file_path))
    if not patch or not patch.items:
        raise RuntimeError(f'Failed to parse patch file: "{file_path}"')
    return patch


def _rewrite_path(prefix: bytes, path: bytes) -> bytes:
    """Add prefix if a real path."""
    if path == b"/dev/null":
        return b"/dev/null"
    return prefix + path


def add_prefix_to_patch(
    patch: patch_ng.PatchSet, path_prefix: str
) -> patch_ng.PatchSet:
    """Add a prefix to all file paths in the given patch file."""
    prefix = path_prefix.strip("/").encode()
    if prefix:
        prefix += b"/"

    diff_git = re.compile(
        r"^diff --git (?:(?P<a>a/))?(?P<old>.+) (?:(?P<b>b/))?(?P<new>.+?)[\r\n]*$"
    )
    svn_index = re.compile(rb"^Index: (.+)$")

    for file in patch.items:
        file.source = _rewrite_path(prefix, file.source)
        file.target = _rewrite_path(prefix, file.target)

        for idx, line in enumerate(file.header):

            git_match = diff_git.match(line.decode("utf-8", errors="replace"))
            if git_match:
                file.header[idx] = (
                    b"diff --git "
                    + (git_match.group("a").encode() if git_match.group("a") else b"")
                    + _rewrite_path(prefix, git_match.group("old").encode())
                    + b" "
                    + (git_match.group("b").encode() if git_match.group("b") else b"")
                    + _rewrite_path(prefix, git_match.group("new").encode())
                )
                break

            svn_match = svn_index.match(line)
            if svn_match:
                file.header[idx] = b"Index: " + _rewrite_path(
                    prefix, svn_match.group(1)
                )
                break

    return patch


def convert_patch_to(patch: patch_ng.PatchSet, required_type: str) -> patch_ng.PatchSet:
    """Convert the patch to the required type."""
    if required_type == patch.type:
        return patch

    if required_type == patch_ng.GIT:
        for file in patch.items:
            file.header = [
                b"diff --git "
                + _rewrite_path(b"a/", file.source)
                + b" "
                + _rewrite_path(b"b/", file.target)
                + b"\n"
            ]
            file.type = required_type
    elif required_type == patch_ng.SVN:
        for file in patch.items:
            file.header = [b"Index: " + file.target + b"\n", b"=" * 67 + b"\n"]
            file.type = required_type
    patch.type = required_type

    return patch
