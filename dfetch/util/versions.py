"""Module for handling version information from strings."""

import re
from collections import defaultdict
from typing import Dict, List, Tuple

from semver import VersionInfo

BASEVERSION = re.compile(
    r"""[vV]?
        (?P<major>0|[1-9]\d*)
        (\.
        (?P<minor>0|[1-9]\d*)
        (\.
            (?P<patch>0|[1-9]\d*)
        )?
        )?
    """,
    re.VERBOSE,
)


def coerce(version: str) -> Tuple[str, VersionInfo, str]:
    """Convert an incomplete version string into a semver-compatible Version object.

    * Tries to detect a "basic" version string (``major.minor.patch``).
    * If not enough components can be found, missing components are
        set to zero to obtain a valid semver version.

    :param str version: the version string to convert
    :return: a tuple with a prefix string, a :class:`Version` instance (or ``None``
        if it's not a version) and the rest of the string which doesn't
        belong to a basic version.
    :rtype: tuple(None, str | :class:`Version` | None, str)
    """
    match = None if not version else BASEVERSION.search(version)
    if not match:
        return ("", None, version)

    ver = {
        key: 0 if value is None else value for key, value in match.groupdict().items()
    }

    return (
        match.string[: match.start()],
        VersionInfo(**ver),
        match.string[match.end() :],  # noqa:E203
    )


def latest_tag_from_list(current_tag: str, available_tags: List[str]) -> str:
    """Based on the given tag string and list of tags, get the latest available."""
    parsed_tags: Dict[str, List[Tuple[VersionInfo, str]]] = defaultdict(list)
    for available_tag in available_tags:
        prefix, version, _ = coerce(available_tag)
        if version:
            parsed_tags[prefix] += [(version, available_tag)]

    prefix, version, _ = coerce(current_tag)

    available_tag, available_string = version, current_tag
    for tag in parsed_tags[prefix]:
        if tag[0] > available_tag:
            available_tag, available_string = tag

    return available_string
