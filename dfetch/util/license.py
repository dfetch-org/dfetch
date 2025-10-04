"""*Dfetch* uses *Infer-License* to guess licenses from files."""

from dataclasses import dataclass
from os import PathLike
from typing import Optional, Union

import infer_license
from infer_license.types import License as InferredLicense


@dataclass
class License:
    """Class to hold license information."""

    name: str  # SPDX Full name
    spdx_id: str  # SPDX Identifier
    trove_classifier: Optional[str]
    probability: float

    @staticmethod
    def from_inferred(
        inferred_license: InferredLicense, probability: float
    ) -> "License":
        """Create License from an InferredLicense."""
        return License(
            name=inferred_license.name,
            spdx_id=inferred_license.shortname,
            trove_classifier=inferred_license.trove_classifier,
            probability=probability,
        )


def guess_license_in_file(
    filename: Union[str, PathLike[str]],
) -> Optional[License]:
    """Guess license from file."""
    try:
        with open(filename, encoding="utf-8") as f:
            license_text = f.read()
    except UnicodeDecodeError:
        with open(filename, encoding="latin-1") as f:
            license_text = f.read()

    probable_license = infer_license.api.probabilities(license_text)

    return None if not probable_license else License.from_inferred(*probable_license[0])
