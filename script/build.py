#!/usr/bin/env python3
"""This script builds the dfetch executable using Nuitka."""
import subprocess  # nosec
import sys
import tomllib as toml
from typing import Union

from dfetch import __version__


def parse_option(
    option_name: str, option_value: Union[bool, str, list, dict]
) -> list[str]:
    """
    Convert a config value to Nuitka CLI arguments.

    Handles booleans (--flag), strings (--flag=value), lists (multiple --flag=value),
    and nested dicts (--flag=key1=val1=key2=val2).

    Returns:
    list[str]: Nuitka CLI arguments in the format ['--flag', '--key=value']
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
with open("pyproject.toml", "rb") as pyproject_file:
    pyproject = toml.load(pyproject_file)
nuitka_opts = pyproject.get("tool", {}).get("nuitka", {})


if sys.platform.startswith("win"):
    nuitka_opts["output-filename"] = nuitka_opts["output-filename-win"]
elif sys.platform.startswith("linux"):
    nuitka_opts["output-filename"] = nuitka_opts["output-filename-linux"]
elif sys.platform.startswith("darwin"):
    nuitka_opts["output-filename"] = nuitka_opts["output-filename-macos"]


nuitka_opts = {
    k: v
    for k, v in nuitka_opts.items()
    if k
    not in {"output-filename-win", "output-filename-linux", "output-filename-macos"}
}

command = [sys.executable, "-m", "nuitka"]
for key, value in nuitka_opts.items():
    command.extend(parse_option(key, value))

command.append("dfetch")

print(command)
subprocess.check_call(command)  # nosec
