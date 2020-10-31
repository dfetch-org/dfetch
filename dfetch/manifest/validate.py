"""Validate manifests."""
import logging

import pykwalify
from pykwalify.core import Core, SchemaError
from yaml.scanner import ScannerError

from dfetch.resources import SCHEMA_PATH


def validate(path: str) -> None:
    """Validate the given manifest."""
    logging.getLogger(pykwalify.__name__).setLevel(logging.CRITICAL)

    with SCHEMA_PATH as schema_path:
        try:
            validator = Core(source_file=path, schema_files=[str(schema_path)])
        except ScannerError as err:
            raise RuntimeError(f"{schema_path} is not a valid YAML file!") from err

    try:
        validator.validate(raise_exception=True)
    except SchemaError as err:
        raise RuntimeError(err.msg) from err
