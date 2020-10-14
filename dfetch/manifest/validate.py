"""
Validate manifests
"""
import logging
import os

import pykwalify
from pykwalify.core import Core, SchemaError
from yaml.scanner import ScannerError

from dfetch.util.util import find_file

SCRIPT_PATH = os.path.dirname(__file__)


def validate(path: str) -> None:
    """ Validate the given manifest """
    logging.getLogger(pykwalify.__name__).setLevel(logging.CRITICAL)

    schema_path = _find_schema()

    try:
        validator = Core(source_file=path, schema_files=[schema_path])
    except ScannerError as err:
        raise RuntimeError(f"{schema_path} is not a valid YAML file!") from err

    try:
        validator.validate(raise_exception=True)
    except SchemaError as err:
        raise RuntimeError(err.msg) from err


def _find_schema() -> str:
    paths = find_file("schema.yaml", SCRIPT_PATH)

    if len(paths) == 0:
        raise RuntimeError("No schema was found!")
    if len(paths) != 1:
        raise RuntimeError(f"Multiple schemas found: {paths}")

    return os.path.realpath(paths[0])
