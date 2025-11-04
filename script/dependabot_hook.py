#!/usr/bin/env python3
"""This file performs any updates needed after a Dependabot PR."""

import re
import sys
from pathlib import Path
from typing import Optional

# Config
SBOM_FILE = "sbom.json"  # path to your CycloneDX SBOM
PYPROJECT_FILE = "pyproject.toml"
PACKAGE_NAME = "cyclonedx-python-lib"
FEATURE_FILE = "features/report-sbom.feature"


def get_new_version_from_pyproject(name: str) -> str:
    """Extract the updated version of a package from pyproject.toml assuming '==' pin."""
    content = Path(PYPROJECT_FILE).read_text(encoding="UTF-8")

    # Match lines like: cyclonedx-python-lib=="11.5.0"
    pattern = re.compile(rf'{re.escape(name)}==["\']?([\d\.]+)["\']?', re.MULTILINE)

    match = pattern.search(content)
    if match:
        return match.group(1)

    raise ValueError(f"{name} not found in {PYPROJECT_FILE}")


def replace_cyclonedx_version_if_outdated(
    new_version: str,
) -> Optional[str]:
    """Update the SBOM JSON file with the new version"""
    feature_file_path = Path(FEATURE_FILE)
    content = feature_file_path.read_text(encoding="UTF-8")

    pattern = re.compile(
        r'("name":\s*"cyclonedx-python-lib",\s*'
        r'"type":\s*"library",\s*'
        r'"version":\s*")(?P<version>[^"]+)(")',
        re.MULTILINE,
    )

    match = pattern.search(content)
    if not match:
        print("Error: cyclonedx-python-lib block not found in feature file")
        sys.exit(1)

    old_version = match.group("version")
    if old_version == new_version:
        print(f'No update needed: "{PACKAGE_NAME}" is already {new_version}')
        return None

    def replacer(m):
        return m.group(1) + new_version + m.group(3)

    new_content = pattern.sub(replacer, content)
    feature_file_path.write_text(new_content, encoding="UTF-8")
    print(
        f'Updated "{PACKAGE_NAME}" version: {old_version} → {new_version} in "{FEATURE_FILE}"'
    )
    return old_version


def main():
    """Main entry point."""
    new_version = get_new_version_from_pyproject("cyclonedx-python-lib")
    replace_cyclonedx_version_if_outdated(new_version)


if __name__ == "__main__":
    main()
