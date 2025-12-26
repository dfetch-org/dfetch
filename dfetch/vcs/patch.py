"""Various patch utilities for VCS systems."""

import difflib
import hashlib
import stat
from collections.abc import Sequence
from pathlib import Path

import patch_ng


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
            patch_lines.append(headline.rstrip(b"\n").decode("utf-8"))
        patch_lines.append(f"--- {p.source.decode('utf-8')}")
        patch_lines.append(f"+++ {p.target.decode('utf-8')}")
        for h in p.hunks:
            patch_lines.append(
                f"@@ -{h.startsrc},{h.linessrc} +{h.starttgt},{h.linestgt} @@"
            )
            for line in h.text:
                patch_lines.append(line.rstrip(b"\n").decode("utf-8"))
    return "\n".join(patch_lines) + "\n" if patch_lines else ""


def create_svn_patch_for_new_file(file_path: str) -> str:
    """Create a svn patch for a new file."""
    diff = unified_diff_new_file(Path(file_path))
    return "" if not diff else "\n".join([f"Index: {file_path}", "=" * 67] + diff)


def create_git_patch_for_new_file(file_path: str) -> str:
    """Create a Git patch for a new untracked file, preserving file mode."""
    path = Path(file_path)
    diff = unified_diff_new_file(path)

    return (
        ""
        if not diff
        else "\n".join(
            [
                f"diff --git a/{file_path} b/{file_path}",
                f"new file mode {_git_mode(path)}",
                f"index 0000000..{_git_blob_sha1(path)[:7]}",
            ]
            + diff
        )
    )


def unified_diff_new_file(path: Path) -> list[str]:
    """Create a unified diff for a new file."""
    with path.open("r", encoding="utf-8", errors="replace") as new_file:
        lines = new_file.readlines()

    return list(
        difflib.unified_diff(
            [], lines, fromfile="/dev/null", tofile=str(path), lineterm=""
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
