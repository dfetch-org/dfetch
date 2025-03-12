#!/usr/bin/env python3

"""Script for simplifying the release."""

import glob
import os
import re
from datetime import datetime

from dfetch import __version__


def replace_pattern_in_files(file_path_pattern, search_pattern, replacement, flags=0):
    """
    Searches for a given pattern in all matching files and replaces it with the specified replacement.

    Args:
        file_path_pattern (str): The glob pattern for files to search (e.g., "./**/*.feature").
        search_pattern (str): The regex pattern to search for in files.
        replacement (str): The replacement string.
        flags (int): Optional regex flags (e.g., re.DOTALL for multiline matching).
    """
    pattern = re.compile(search_pattern, flags)

    files_changed = []

    for file_path in glob.glob(file_path_pattern, recursive=True):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = pattern.sub(replacement, content)

        if content != new_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            files_changed.append(file_path)
    print(
        f"Replaced '{search_pattern}' with '{replacement}' in {len(files_changed)} files"
    )


if __name__ == "__main__":
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

    replace_pattern_in_files(
        file_path_pattern=f"{base_dir}/CHANGELOG.rst",
        search_pattern=r"(Release \d+\.\d+\.\d+) \(unreleased\)",
        replacement=r"\1 (released " + datetime.now().strftime("%Y-%m-%d") + ")",
        flags=re.DOTALL,
    )

    replace_pattern_in_files(
        file_path_pattern=f"{base_dir}/**/*.feature",
        search_pattern=r"Dfetch \((\d+)\.(\d+)\.(\d+)\)",
        replacement=f"Dfetch ({__version__})",
    )

    # replace_pattern_in_files(
    #     file_path_pattern=f"{base_dir}/features/report-sbom.feature",
    #     search_pattern=r'("name":\s*"dfetch",\s*"version":\s*")\d+\.\d+\.\d+(")',
    #     replacement=r"\1" + __version__ + r"\2",
    #     flags=re.DOTALL,
    # )
