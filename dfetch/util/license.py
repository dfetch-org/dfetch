"""*Dfetch* uses *Infer-License* to guess licenses from files."""

import os
from typing import Optional, Tuple, Union

import infer_license
from infer_license.types import License

LICENSE_PROBABILITY_THRESHOLD = 0.80


def guess_license_in_file(
    filename: Union[str, "os.PathLike[str]"],
) -> Tuple[Optional[License], float]:
    """Guess license from file."""
    try:
        with open(filename, encoding="utf-8") as f:
            license_text = f.read()
    except UnicodeDecodeError:
        with open(filename, encoding="latin-1") as f:
            license_text = f.read()

    probable_license = infer_license.api.probabilities(license_text)
    if probable_license and probable_license[0][1] > LICENSE_PROBABILITY_THRESHOLD:
        return probable_license[0]

    return None, 0.0
