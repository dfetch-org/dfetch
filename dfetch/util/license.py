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
    trove_classifier: Optional[str]  # Python package classifier
    probability: float  # Confidence level of the license inference

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
    """Attempt to identify the license of a given file.

    Args:
        filename (Union[str, os.PathLike[str]]): Path to the file to analyze

    Returns:
        Optional[License]: The most probable license if found, None if no license could be detected
    """
    try:
        with open(filename, "rb") as f:
            file_bytes = f.read()
        try:
            license_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            license_text = file_bytes.decode("latin-1")
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        # Return None for file access issues
        return None
    except OSError:
        # Handle other OS-level file errors
        return None

    probable_licenses = infer_license.api.probabilities(license_text)

    return (
        None if not probable_licenses else License.from_inferred(*probable_licenses[0])
    )
