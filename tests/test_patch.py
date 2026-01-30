"""Test the patch module."""

# mypy: ignore-errors
# flake8: noqa

import pytest

from dfetch.vcs.patch import (
    create_git_patch_for_new_file,
    create_svn_patch_for_new_file,
    reverse_patch,
)


def test_create_git_patch_for_new_file(tmp_path):
    """Check basic patch generation for new files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World\n\nLine above is empty\n")

    actual_patch = create_git_patch_for_new_file(str(test_file))

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

    assert actual_patch == expected_patch


def test_create_svn_patch_for_new_file(tmp_path):
    """Check basic patch generation for new files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World\n\nLine above is empty\n")

    actual_patch = create_svn_patch_for_new_file(str(test_file))

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

    assert actual_patch == expected_patch


def test_reverse_patch():
    """Check reversing a patch."""
    patch = b"""
Index: README.md
===================================================================
--- README.md
+++ README.md
@@ -1,1 +1,2 @@
 Patched file for SomeProject
+Update to patched file for SomeProject
"""

    reversed_patch = reverse_patch(patch)

    expected = """
Index: README.md
===================================================================
--- README.md
+++ README.md
@@ -1,2 +1,1 @@
 Patched file for SomeProject
-Update to patched file for SomeProject
"""

    assert reversed_patch == expected


def test_reverse_patch_order():
    """Check reversing a patch."""
    patch = b"""
Index: README.md
===================================================================
--- README.md
+++ README.md
@@ -1,1 +1,2 @@
-Patched file for SomeProject
-Update to patched file for SomeProject
+Generated file for SomeProject

"""

    reversed_patch = reverse_patch(patch)

    expected = """
Index: README.md
===================================================================
--- README.md
+++ README.md
@@ -1,1 +1,2 @@
-Generated file for SomeProject
+Patched file for SomeProject
+Update to patched file for SomeProject

"""

    assert reversed_patch == expected
