#!/usr/bin/env python3
"""This script packages the dfetch build directory into OS-specific installers using fpm."""
import shutil
import subprocess
import sys
from pathlib import Path

from dfetch import __version__

# Configuration
BUILD_DIR = Path("build", "dfetch.dist")
OUTPUT_DIR = Path("build", "dfetch-package")
PACKAGE_NAME = "dfetch"
INSTALL_PREFIX = "/opt/dfetch"  # Where the files will be installed on Linux/macOS
MAINTAINER = "DFetch Team <dfetch@spoor.cc>"
DESCRIPTION = (
    "DFetch: A vendoring tool for fetching and managing external dependencies."
)
URL = "https://github.com/dfetch-org/dfetch"
LICENSE = "MIT"


def run_command(command):
    """Run a system command and handle errors."""
    command[0] = shutil.which(command[0])  # On windows .bat files need full path

    if not command[0]:
        raise FileNotFoundError(f"Command not found: {command[0]}")

    print("Running:", " ".join(command))
    subprocess.check_call(command)


def package_linux() -> None:
    """Package the build directory into .deb and .rpm installers."""
    for target in ("deb", "rpm"):
        output = f"{OUTPUT_DIR}/{PACKAGE_NAME}_{__version__}.{target}"
        cmd = [
            "fpm",
            "-s",
            "dir",
            "-t",
            target,
            "-n",
            PACKAGE_NAME,
            "-v",
            __version__,
            "-C",
            str(BUILD_DIR),
            "--prefix",
            INSTALL_PREFIX,
            "--description",
            DESCRIPTION,
            "--maintainer",
            MAINTAINER,
            "--url",
            URL,
            "--license",
            LICENSE,
            "-p",
            output,
            ".",
        ]
        run_command(cmd)


def package_macos() -> None:
    """Package the build directory into a .pkg installer for macOS."""
    cmd = [
        "fpm",
        "-s",
        "dir",
        "-t",
        "osxpkg",
        "-n",
        PACKAGE_NAME,
        "-v",
        __version__,
        "-C",
        str(BUILD_DIR),
        "--prefix",
        INSTALL_PREFIX,
        "--description",
        DESCRIPTION,
        "--maintainer",
        MAINTAINER,
        "--url",
        URL,
        "--license",
        LICENSE,
        "-p",
        f"{OUTPUT_DIR}/{PACKAGE_NAME}_{__version__}.pkg",
        ".",
    ]
    run_command(cmd)


def package_windows() -> None:
    """Package the build directory into a .msi installer for Windows."""
    cmd = [
        "fpm",
        "-s",
        "dir",
        "-t",
        "msi",
        "-n",
        PACKAGE_NAME,
        "-v",
        __version__,
        "-C",
        str(BUILD_DIR),
        "--description",
        DESCRIPTION,
        "--maintainer",
        MAINTAINER,
        "--url",
        URL,
        "--license",
        LICENSE,
        "-p",
        f"{OUTPUT_DIR}/{PACKAGE_NAME}_{__version__}.msi",
        ".",
    ]
    run_command(cmd)


def main() -> None:
    """Main packaging function."""
    if not BUILD_DIR.exists():
        print(f"Error: Build directory {BUILD_DIR} does not exist. Run build.py first.")
        sys.exit(1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if sys.platform.startswith("linux"):
        package_linux()
    elif sys.platform.startswith("darwin"):
        package_macos()
    elif sys.platform.startswith("win"):
        package_windows()
    else:
        print(f"Unsupported platform: {sys.platform}")
        sys.exit(1)


if __name__ == "__main__":
    main()
