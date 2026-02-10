"""Test the patch module."""

# mypy: ignore-errors
# flake8: noqa

import difflib
import tempfile
import textwrap
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dfetch.util.util import in_directory
from dfetch.vcs.patch import (
    Patch,
    PatchType,
    _reverse_patch,
)


def _normalize(patch: str) -> str:
    """Normalize patch text for stable comparisons."""
    return textwrap.dedent(patch).lstrip("\r\n").rstrip() + "\n"


def test_create_git_patch_for_new_file(tmp_path):
    """Check basic patch generation for new files."""
    test_file = Path("test.txt")

    with in_directory(tmp_path):
        test_file.write_text("Hello World\n\nLine above is empty\n")
        actual_patch = Patch._for_new_file(str(test_file), PatchType.GIT)

    expected_patch = "\n".join(
        [
            f"diff --git a/{test_file} b/{test_file}",
            "new file mode 100644",
            "index 0000000..8029fa5",
            "--- /dev/null",
            f"+++ {test_file}",
            "@@ -0,0 +1,3 @@",
            "+Hello World",
            "+",
            "+Line above is empty",
            "",
        ]
    )

    assert actual_patch.dump() == expected_patch


def test_create_svn_patch_for_new_file(tmp_path):
    """Check basic patch generation for new files."""
    test_file = Path("test.txt")

    with in_directory(tmp_path):
        test_file.write_text("Hello World\n\nLine above is empty\n")
        actual_patch = Patch._for_new_file(str(test_file), PatchType.SVN)

    expected_patch = "\n".join(
        [
            f"Index: {test_file}",
            "===================================================================",
            "--- /dev/null",
            f"+++ {test_file}",
            "@@ -0,0 +1,3 @@",
            "+Hello World",
            "+",
            "+Line above is empty",
            "",
        ]
    )

    assert actual_patch.dump() == expected_patch


def test_reverse_patch_simple_addition():
    """Test reversing a simple addition patch."""
    patch = _normalize("""
        Index: README.md
        ===================================================================
        --- README.md
        +++ README.md
        @@ -1,1 +1,2 @@
         Patched file for SomeProject
        +Update to patched file for SomeProject
    """)

    expected = _normalize("""
        Index: README.md
        ===================================================================
        --- README.md
        +++ README.md
        @@ -1,2 +1,1 @@
         Patched file for SomeProject
        -Update to patched file for SomeProject
    """)

    assert _reverse_patch(patch) == expected


def test_reverse_patch_replacement_order():
    """Test reversing a replacement patch."""
    patch = _normalize("""
        Index: README.md
        ===================================================================
        --- README.md
        +++ README.md
        @@ -1,2 +1,1 @@
        -Patched file for SomeProject
        -Update to patched file for SomeProject
        +Generated file for SomeProject
    """)

    expected = _normalize("""
        Index: README.md
        ===================================================================
        --- README.md
        +++ README.md
        @@ -1,1 +1,2 @@
        -Generated file for SomeProject
        +Patched file for SomeProject
        +Update to patched file for SomeProject
    """)

    assert _reverse_patch(patch) == expected


def test_reverse_patch_mixed_context():
    """Test reversing a patch with mixed additions and deletions."""
    patch = _normalize("""
        --- a/file.txt
        +++ b/file.txt
        @@ -1,4 +1,4 @@
         line one
        -line two
        +line TWO
         line three
         line four
    """)

    expected = _normalize("""
        --- b/file.txt
        +++ a/file.txt
        @@ -1,4 +1,4 @@
         line one
        -line TWO
        +line two
         line three
         line four
    """)

    assert _reverse_patch(patch) == expected


def test_reverse_patch_multiple_hunks():
    """Test reversing a patch with multiple hunks."""
    patch = _normalize("""
        --- a/file.txt
        +++ b/file.txt
        @@ -1,2 +1,2 @@
        -old line 1
        +new line 1
         unchanged
        @@ -5,2 +5,3 @@
         context
        +added line
         more context
    """)

    expected = _normalize("""
        --- b/file.txt
        +++ a/file.txt
        @@ -1,2 +1,2 @@
        -new line 1
        +old line 1
         unchanged
        @@ -5,3 +5,2 @@
         context
        -added line
         more context
    """)

    assert _reverse_patch(patch) == expected


def test_reverse_patch_file_creation():
    """Test reversing a file creation patch."""
    patch = _normalize("""
        --- /dev/null
        +++ b/newfile.txt
        @@ -0,0 +1,2 @@
        +hello
        +world
    """)

    expected = _normalize("""
        --- b/newfile.txt
        +++ /dev/null
        @@ -1,2 +0,0 @@
        -hello
        -world
    """)

    assert _reverse_patch(patch) == expected


def test_reverse_patch_file_deletion():
    """Test reversing a file deletion patch."""
    patch = _normalize("""
        --- a/oldfile.txt
        +++ /dev/null
        @@ -1,2 +0,0 @@
        -goodbye
        -cruel world
    """)

    expected = _normalize("""
        --- /dev/null
        +++ a/oldfile.txt
        @@ -0,0 +1,2 @@
        +goodbye
        +cruel world
    """)

    assert _reverse_patch(patch) == expected


def test_reverse_patch_zero_length_hunk():
    """Test reversing a patch with a zero-length hunk (insertion)."""
    patch = _normalize("""
        --- a/file.txt
        +++ b/file.txt
        @@ -3,0 +3,1 @@
        +inserted
    """)

    expected = _normalize("""
        --- b/file.txt
        +++ a/file.txt
        @@ -3,1 +3,0 @@
        -inserted
    """)

    assert _reverse_patch(patch) == expected


# Random small file: 5–15 lines, each line 5–20 chars (filtered to exclude control chars)
st_file_lines = st.lists(
    st.text(
        min_size=5,
        max_size=20,
        alphabet=st.characters(
            blacklist_categories=("Cc", "Cs"), blacklist_characters="\r\n"
        ),
    ),
    min_size=5,
    max_size=15,
)


@settings(max_examples=1000)
@given(original_lines=st_file_lines, rng=st.randoms())
def test_reverse_patch_small_random(original_lines, rng):
    """Test patch generation and reversal on small random files."""
    original = "\n".join(original_lines + [""])

    # Decide randomly: line shuffle OR char shuffle
    if rng.choice([True, False]):
        modified_lines = original_lines[:]
        rng.shuffle(modified_lines)
    else:
        modified_lines = []
        for line in original_lines:
            chars = list(line)
            rng.shuffle(chars)
            modified_lines.append("".join(chars))

    modified = "\n".join(modified_lines + [""])

    # Generate forward and reverse patches
    patch_forward = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile="file.txt",
            tofile="file.txt",
            lineterm="\n",
        )
    )

    patch_reverse = _reverse_patch(patch_forward)

    if not patch_forward:
        # No changes detected; skip
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        target_file = tmp_path / "file.txt"
        target_file.write_text(modified)
        patch_file = tmp_path / "reverse.patch"
        patch_file.write_text(patch_reverse)

        try:
            Patch.from_file(patch_file).apply(root=str(tmp_path))
        except Exception as e:
            pytest.fail(reason=f"Reverse patch failed: {e}")

        restored = target_file.read_text()
        assert restored == original, "Reverse patch did not restore original!"


def test_patch_prefix_new_file(tmp_path):
    """Test adding prefix to new file."""
    original_patch = "\n".join(
        [
            "diff --git a/test.txt b/test.txt",
            "new file mode 100644",
            "index 0000000..8029fa5",
            "--- /dev/null",
            "+++ b/test.txt",
            "@@ -0,0 +1,3 @@",
            "+Hello World",
            "+",
            "+Line above is empty",
            "",
        ]
    )

    original_patch_file = tmp_path / "original.patch"
    original_patch_file.write_text(original_patch)

    expected_patch = "\n".join(
        [
            "diff --git a/src/test.txt b/src/test.txt",
            "new file mode 100644",
            "index 0000000..8029fa5",
            "--- /dev/null",
            "+++ b/src/test.txt",
            "@@ -0,0 +1,3 @@",
            "+Hello World",
            "+",
            "+Line above is empty",
            "",
        ]
    )

    prefixed_patch = Patch.from_file(original_patch_file).add_prefix(
        path_prefix="src",
    )

    assert prefixed_patch.dump() == expected_patch
