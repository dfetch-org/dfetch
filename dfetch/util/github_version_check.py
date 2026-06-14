"""Poll the GitHub releases API to see if a newer dfetch version is available."""

import json
import urllib.error
import urllib.request

from dfetch import __version__
from dfetch.util.versions import coerce

_RELEASES_URL = "https://api.github.com/repos/dfetch-org/dfetch/releases/latest"


def _is_newer(tag: str) -> str | None:
    """Return *tag* (sans leading v/V) when it is newer than the installed version."""
    _, latest, _ = coerce(tag)
    _, current, _ = coerce(__version__)
    if latest and current and latest > current:
        return tag.lstrip("vV")
    return None


def newer_version_available() -> str | None:
    """Return the latest release version string if it is newer than the running version.

    Returns:
        str | None: The newer version string (without leading ``v``), or ``None``
            when the current version is up-to-date or the check cannot be completed.
    """
    try:
        req = urllib.request.Request(
            _RELEASES_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "dfetch"},
        )
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler())
        with opener.open(req, timeout=2) as response:
            data = json.loads(response.read())
        tag = data.get("tag_name")
        if not isinstance(tag, str) or not tag:
            return None
        return _is_newer(tag)
    except (urllib.error.URLError, json.JSONDecodeError, ValueError):
        pass
    return None
