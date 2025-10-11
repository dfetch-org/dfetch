#!/usr/bin/env python3
"""This script builds the dfetch executable using Nuitka."""
import subprocess
import sys
import tomllib as toml
from typing import Union

from dfetch import __version__


def parse_option(
    option_name: str, option_value: Union[bool, str, list, dict]
) -> list[str]:
    """
    Convert a config value to CLI args for Nuitka.
    Handles booleans, strings, lists, and nested dicts.
    """
    args = []
    cli_key = f"--{option_name.replace('_','-')}"

    if isinstance(option_value, bool):
        if option_value:
            args.append(cli_key)
    elif isinstance(option_value, str):
        args.append(f"{cli_key}={option_value}".replace("{VERSION}", __version__))
    elif isinstance(option_value, list):
        for v in option_value:
            if isinstance(v, dict):
                parts = [f"{v[k]}" for k in v]
                args.append(f"{cli_key}={'='.join(parts)}")
            else:
                args.append(f"{cli_key}={v}")
    else:
        args.append(f"{cli_key}={option_value}")

    return args


# Load pyproject.toml
with open("pyproject.toml", "r", encoding="UTF-8") as pyproject_file:
    pyproject = toml.loads(pyproject_file.read())
nuitka_opts = pyproject.get("tool", {}).get("nuitka", {})


if sys.platform.startswith("win"):
    nuitka_opts["output-filename"] = nuitka_opts["output-filename-win"]
elif sys.platform.startswith("linux"):
    nuitka_opts["output-filename"] = nuitka_opts["output-filename-linux"]
elif sys.platform.startswith("darwin"):
    nuitka_opts["output-filename"] = nuitka_opts["output-filename-macos"]

for key in ["output-filename-win", "output-filename-linux", "output-filename-macos"]:
    nuitka_opts.pop(key, None)

command = [sys.executable, "-m", "nuitka"]
for key, value in nuitka_opts.items():
    command.extend(parse_option(key, value))

command.append("dfetch")

print(command)
subprocess.check_call(command)
