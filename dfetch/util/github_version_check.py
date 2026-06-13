"""Poll the GitHub releases API to see if a newer dfetch version is available."""

import json
import urllib.error
import urllib.request
from typing import Optional

from dfetch import __version__
from dfetch.util.versions import coerce

_RELEASES_URL = (
    "https://api.github.com/repos/dfetch-org/dfetch/releases/latest"
)


def newer_version_available() -> Optional[str]:
    """Return the latest release version string if it is newer than the running version.

    Returns:
        Optional[str]: The newer version string (without leading ``v``), or ``None``
            when the current version is up-to-date or the check cannot be completed.
    """
    try:
        req = urllib.request.Request(
            _RELEASES_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "dfetch"},
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read())
        tag = str(data.get("tag_name", ""))
        _, latest, _ = coerce(tag)
        _, current, _ = coerce(__version__)
        if latest and current and latest > current:
            return tag.lstrip("vV")
    except (urllib.error.URLError, json.JSONDecodeError, ValueError):
        pass
    return None
