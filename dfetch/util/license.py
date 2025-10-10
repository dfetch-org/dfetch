"""*Dfetch* uses *Infer-License* to guess licenses from files."""

from dataclasses import dataclass
from os import PathLike
from typing import Optional, Union

import infer_license
from infer_license.types import License as InferredLicense

# Limit license file size to below number of bytes to prevent memory issues with large files
MAX_LICENSE_FILE_SIZE = 1024 * 1024  # 1 MB


@dataclass
class License:
    """Represents a software license with its SPDX identifiers and detection confidence.

    This class encapsulates license information detected by the infer-license library,
    providing standardized identifiers and confidence level of the detection.
    """

    name: str  #: SPDX Full name
    spdx_id: str  #: SPDX Identifier
    trove_classifier: Optional[str]  #: Python package classifier
    probability: float  #: Confidence level of the license inference

    @staticmethod
    def from_inferred(
        inferred_license: InferredLicense, probability: float
    ) -> "License":
        """Convert an infer-license License object to our internal License representation.

        Args:
            inferred_license: The license object from infer-license library
            probability: The confidence score (0-1) of the license detection

        Returns:
            License: A new License instance with the inferred information
        """
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

    Tries UTF-8 encoding first, falling back to Latin-1 for legacy license files.
    If the file cannot be read or no license is detected, returns None.

    Args:
        filename (Union[str, os.PathLike[str]]): Path to the file to analyze

    Returns:
        Optional[License]: The most probable license if found, None if no license could be detected
    """
    try:
        with open(filename, "rb") as f:
            file_bytes = f.read(MAX_LICENSE_FILE_SIZE)
        try:
            license_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            license_text = file_bytes.decode("latin-1")
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError):
        return None

    probable_licenses = infer_license.api.probabilities(license_text)

    return (
        None if not probable_licenses else License.from_inferred(*probable_licenses[0])
    )
