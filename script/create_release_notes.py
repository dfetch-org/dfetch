#!/usr/bin/env python3
"""
create_release_notes.py

Extracts the latest section from CHANGELOG.rst.
"""

import argparse
import re
import sys
from pathlib import Path


def extract_latest_section(changelog_path: Path) -> str:
    """Extract the latest release section from a CHANGELOG file."""

    content = changelog_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    version_header_pattern = re.compile(r"^Release \d+\.\d+\.\d+")

    start_idx, end_idx = None, None

    for idx, line in enumerate(lines):
        if version_header_pattern.match(line.strip()):
            start_idx = idx
            break

    if start_idx is None:
        raise ValueError(f"No release section found in {changelog_path}")

    for idx in range(start_idx + 1, len(lines)):
        if version_header_pattern.match(lines[idx].strip()):
            end_idx = idx
            break

    # If end_idx is None, capture all lines to the end (single release section)
    section_lines = lines[start_idx:end_idx]
    return "\n".join(section_lines).strip()


def main():
    """Main CLI entry."""
    parser = argparse.ArgumentParser(
        description="Create release notes from CHANGELOG.rst"
    )
    parser.add_argument(
        "--changelog", default="CHANGELOG.rst", help="Path to CHANGELOG.rst"
    )
    args = parser.parse_args()

    changelog_path = Path(args.changelog)
    if not changelog_path.exists():
        print(f"Error: {changelog_path} not found.")
        sys.exit(1)

    Path("release_notes.txt").write_text(
        extract_latest_section(changelog_path), encoding="UTF-8"
    )


if __name__ == "__main__":
    main()
