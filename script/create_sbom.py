#!/usr/bin/env python3
"""Generate an sbom of the tool."""
import contextlib
import logging
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from dfetch import __version__

logging.basicConfig(level=logging.INFO)

PROJECT_DIR = Path(__file__).parent.parent.resolve()
OUTPUT_FILE = PROJECT_DIR / f"dfetch-{__version__}.{sys.platform}.cdx.json"

DEPS = f"{PROJECT_DIR}[sbom]"


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
    subprocess.check_call([python, "-m", "pip", "install", DEPS])
    subprocess.check_call(
        [python, "-m", "cyclonedx_py", "environment", "-o", str(OUTPUT_FILE)]
    )

logging.info(f"SBOM generated at {OUTPUT_FILE}")
