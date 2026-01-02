#!/usr/bin/env python3
"""Generate an sbom of the tool."""
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


PLATFORM_NAME = "nix"

if sys.platform.startswith("darwin"):
    PLATFORM_NAME = "osx"
elif sys.platform.startswith("win"):
    PLATFORM_NAME = "win"


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


with temporary_venv() as python:
    subprocess.check_call([python, "-m", "pip", "install", DEPS])  # nosec

    __version__ = (
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

    OUTPUT_FILE = (
        PROJECT_DIR
        / "build"
        / "dfetch-package"
        / f"dfetch-{__version__}-{PLATFORM_NAME}.cdx.json"
    )
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(  # nosec
        [python, "-m", "cyclonedx_py", "environment", "-o", str(OUTPUT_FILE)]
    )

logging.info(f"SBOM generated at {OUTPUT_FILE}")
