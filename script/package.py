#!/usr/bin/env python3
"""This script packages the dfetch build directory into OS-specific installers using fpm & wix."""
import shutil
import subprocess  # nosec
import sys
import tomllib as toml
import xml.etree.ElementTree as ET  # nosec (only used for XML generation, not parsing untrusted input)
from pathlib import Path

from setuptools_scm import get_version

from dfetch import __version__ as __digit_only_version__  # Used inside the installers

__version__ = get_version(  # Used to name the installers
    root=".",
    version_scheme="guess-next-dev",
    local_scheme="no-local-version",
)

# Configuration loading
with open("pyproject.toml", "rb") as pyproject_file:
    pyproject = toml.load(pyproject_file)
project_info = pyproject.get("project", {})

PACKAGE_NAME = project_info.get("name")

MAINTAINER = project_info.get("authors", [{}])[0].get("name", "")
DESCRIPTION = project_info.get("description", "")
URL = project_info.get("urls", {}).get("Homepage", "")
DOCS_URL = project_info.get("urls", {}).get("Documentation", "")
ISSUES_URL = project_info.get("urls", {}).get("Issues", "")
CHANGELOG_URL = project_info.get("urls", {}).get("Changelog", "")
LICENSE = project_info.get("license", "")

INSTALL_PREFIX = (
    f"/opt/{PACKAGE_NAME}"  # Where the files will be installed on Linux/macOS
)
BUILD_DIR = Path("build", f"{PACKAGE_NAME}.dist")
OUTPUT_DIR = Path("build", f"{PACKAGE_NAME}-package")
UPGRADE_CODE = "BDC7DA0D-70C1-4189-BE88-F1BD2DEE3E33"  #: Fixed UUID for WiX installer, must be unique and stable

tools = pyproject.get("tool", {})
nuitka_info = tools.get("nuitka", {})

WINDOWS_ICO = nuitka_info.get("windows-icon-from-ico", "")
WINDOWS_ICO_PATH = Path(WINDOWS_ICO).resolve() if WINDOWS_ICO else None


PLATFORM_NAME = "nix"

if sys.platform.startswith("darwin"):
    PLATFORM_NAME = "osx"
elif sys.platform.startswith("win"):
    PLATFORM_NAME = "win"


def run_command(command: list[str]) -> None:
    """Run a system command and handle errors."""
    resolved_cmd = shutil.which(command[0])
    if not resolved_cmd:
        raise FileNotFoundError(f"Command not found: {command[0]}")

    command[0] = resolved_cmd  # On windows .bat files need full path

    print("Running:", " ".join(command))
    subprocess.check_call(command)  # nosec


def package_linux() -> None:
    """Package the build directory into .deb and .rpm installers."""
    for target in ("deb", "rpm"):
        output = f"{OUTPUT_DIR}/{PACKAGE_NAME}-{__version__}-{PLATFORM_NAME}.{target}"
        cmd = [
            "fpm",
            "-s",
            "dir",
            "-t",
            target,
            "-n",
            PACKAGE_NAME,
            "-v",
            __digit_only_version__,
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
        __digit_only_version__,
        "-C",
        str(BUILD_DIR),
        # https://github.com/jordansissel/fpm/issues/1996 This prefix results in /opt/dfetch/opt/dfetch
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
        f"{OUTPUT_DIR}/{PACKAGE_NAME}-{__version__}-{PLATFORM_NAME}.pkg",
        ".",
    ]
    run_command(cmd)


def check_wix_installed() -> None:
    """Check if WiX Toolset v4 is installed (candle.exe & light.exe)."""
    wix = shutil.which("wix.exe")
    if not wix:
        print(
            "Error: WiX Toolset v4 is required but not found.\n"
            "Please install it from https://wixtoolset.org/releases/\n"
            "and ensure 'wix.exe' is in your PATH."
        )
        sys.exit(1)


def generate_wix_xml(build_dir: Path, output_wxs: Path) -> None:
    """Generate a minimal WiX v4 XML including all files in build_dir."""
    wix = ET.Element("Wix", xmlns="http://wixtoolset.org/schemas/v4/wxs")
    package = ET.SubElement(
        wix,
        "Package",
        Name=PACKAGE_NAME,
        Manufacturer=MAINTAINER,
        Version=__digit_only_version__,
        UpgradeCode=UPGRADE_CODE,
    )

    ET.SubElement(package, "MediaTemplate", EmbedCab="yes")

    standard_dir = ET.SubElement(
        package,
        "StandardDirectory",
        Id="ProgramFilesFolder",
    )
    install_dir = ET.SubElement(
        standard_dir, "Directory", Id="INSTALLFOLDER", Name=PACKAGE_NAME
    )

    component = ET.SubElement(
        install_dir,
        "Component",
        Id="MainComponent",
        Guid="*",
        Directory="INSTALLFOLDER",
    )

    ET.SubElement(
        component,
        "Environment",
        Id="AddToPath",
        Name="PATH",
        Value="[INSTALLFOLDER]",
        Action="set",
        Part="last",
        System="yes",
    )

    # Registry key so InstallLocation is discoverable
    ET.SubElement(
        component,
        "RegistryValue",
        Root="HKLM",
        Key=f"Software\\{PACKAGE_NAME}",
        Name="InstallLocation",
        Value="[INSTALLFOLDER]",
        Type="string",
        KeyPath="yes",
    )

    # Feature
    feature = ET.SubElement(
        package,
        "Feature",
        Id="MainFeature",
        Title=PACKAGE_NAME,
        Level="1",
    )

    ET.SubElement(
        feature,
        "ComponentRef",
        Id="MainComponent",
    )
    ET.SubElement(feature, "Files", Include=str(build_dir.resolve() / "**"))

    # Add / Remove programs info (ARP)
    ET.SubElement(package, "Property", Id="ARPCOMMENTS", Value=DESCRIPTION)
    ET.SubElement(package, "Property", Id="ARPURLINFOABOUT", Value=URL)
    ET.SubElement(package, "Property", Id="ARPREADME", Value=DOCS_URL)
    ET.SubElement(package, "Property", Id="ARPHELPLINK", Value=ISSUES_URL)
    ET.SubElement(package, "Property", Id="ARPURLUPDATEINFO", Value=CHANGELOG_URL)

    if WINDOWS_ICO_PATH:
        ET.SubElement(package, "Icon", Id="AppIcon", SourceFile=str(WINDOWS_ICO_PATH))
        ET.SubElement(package, "Property", Id="ARPPRODUCTICON", Value="AppIcon")

    # Don't show modify & repair buttons, only remove
    ET.SubElement(package, "Property", Id="ARPNOMODIFY", Value="1")
    ET.SubElement(package, "Property", Id="ARPNOREPAIR", Value="1")

    tree = ET.ElementTree(wix)
    tree.write(output_wxs, encoding="utf-8", xml_declaration=True)


def generate_wix_proj(output_proj: Path, wix_file: Path) -> None:
    """Generate a minimal WiX SDK project referencing the .wxs file."""
    project = ET.Element("Project", Sdk="WixToolset.Sdk/6.0.2")

    item_group = ET.SubElement(project, "ItemGroup")
    ET.SubElement(item_group, "Wix", Include=str(wix_file))

    tree = ET.ElementTree(project)
    tree.write(output_proj, encoding="utf-8", xml_declaration=True)


def package_windows() -> None:
    """Package the build directory into a .msi installer for Windows using WiX v4."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wix_file = OUTPUT_DIR / f"{PACKAGE_NAME}.wxs"
    wix_proj = OUTPUT_DIR / f"{PACKAGE_NAME}.wixproj"
    msi_file = OUTPUT_DIR / f"{PACKAGE_NAME}-{__version__}-{PLATFORM_NAME}.msi"

    generate_wix_xml(BUILD_DIR, wix_file)
    generate_wix_proj(wix_proj, wix_file)

    check_wix_installed()

    run_command(
        ["dotnet", "build", str(wix_proj), "-c", "Release", "-o", str(OUTPUT_DIR)]
    )

    shutil.move(OUTPUT_DIR / "dfetch.msi", msi_file)

    print(f"MSI generated at {msi_file}")


def list_files(path: Path) -> None:
    """List all files in the given path."""
    for file_path in path.rglob("*"):
        if file_path.is_file():
            print(file_path.relative_to(path))


def main() -> None:
    """Main packaging function."""
    if not BUILD_DIR.exists():
        print(f"Error: Build directory {BUILD_DIR} does not exist. Run build.py first.")
        sys.exit(1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    list_files(BUILD_DIR)

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
