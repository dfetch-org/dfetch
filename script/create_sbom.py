#!/usr/bin/env python3
"""Generate an sbom of the tool."""

import argparse
import contextlib
import logging
import subprocess  # nosec
import sys
import tempfile
import venv
from pathlib import Path

logging.basicConfig(level=logging.INFO)

PROJECT_DIR = Path(__file__).parent.parent.resolve()

DEPS = f"{PROJECT_DIR}[sbom]"

PLATFORM_MAPPING = {
    "darwin": "osx",
    "win": "win",
}
PLATFORM_NAME = next(
    (
        name
        for prefix, name in PLATFORM_MAPPING.items()
        if sys.platform.startswith(prefix)
    ),
    "nix",
)


@contextlib.contextmanager
def temporary_venv():
    """Create a temporary virtual environment and clean it up on exit."""
    with tempfile.TemporaryDirectory(prefix="venv_sbom_") as tmpdir:
        venv_dir = Path(tmpdir)
        logging.info(f"Creating temporary virtual environment at {venv_dir}")
        venv.create(venv_dir, with_pip=True, upgrade_deps=True)

        if sys.platform.startswith("win"):
            python_bin = venv_dir / "Scripts" / "python.exe"
        else:
            python_bin = venv_dir / "bin" / "python"

        yield str(python_bin)


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate a CycloneDX SBOM for dfetch.")
    parser.add_argument(
        "--py",
        action="store_true",
        help="Generate SBOM for the Python distribution instead of the platform binary.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Directory to write the SBOM into (default: dist/ for --py, build/dfetch-package/ otherwise).",
    )
    return parser.parse_args()


args = parse_args()

if args.py:
    suffix = "py"
    output_dir = args.output_dir or PROJECT_DIR / "dist"
else:
    suffix = PLATFORM_NAME
    output_dir = args.output_dir or PROJECT_DIR / "build" / "dfetch-package"

with temporary_venv() as python:
    subprocess.check_call([python, "-m", "pip", "install", DEPS])  # nosec

    version = (
        subprocess.run(  # nosec
            [
                python,
                "-c",
                "from importlib.metadata import version; print(version('dfetch'))",
            ],
            check=True,
            capture_output=True,
        )
        .stdout.decode("UTF-8")
        .strip()
    )

    output_file = output_dir / f"dfetch-{version}-{suffix}.cdx.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(  # nosec
        [python, "-m", "cyclonedx_py", "environment", "-o", str(output_file)]
    )

logging.info(f"SBOM generated at {output_file}")
