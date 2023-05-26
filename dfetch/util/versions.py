"""Module for handling version information from strings."""

import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from semver.version import Version

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


def coerce(version: str) -> Tuple[str, Optional[Version], str]:
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
        key: 0 if value is None else int(value)
        for key, value in match.groupdict().items()
    }

    return (
        match.string[: match.start()],
        Version(**ver),
        match.string[match.end() :],  # noqa:E203
    )


def latest_tag_from_list(current_tag: str, available_tags: List[str]) -> str:
    """Based on the given tag string and list of tags, get the latest available."""
    parsed_tags = _create_available_version_dict(available_tags)

    prefix, current_version, _ = coerce(current_tag)

    latest_string: str = current_tag

    if current_version:
        latest_tag: Version = current_version
        for tag in parsed_tags[prefix]:
            if tag[0] > latest_tag:
                latest_tag, latest_string = tag

    return latest_string


def _create_available_version_dict(
    available_tags: List[str],
) -> Dict[str, List[Tuple[Version, str]]]:
    """Create a dictionary where each key is a prefix with a list of versions.

    Args:
        available_tags (List[str]): A list of available tags.

    Returns:
        Dict[str, List[Tuple[Version, str]]]: A dictionary mapping prefixes to lists of versions.

    Example:
        >>> available_tags = [
        ...    'release/v1.2.3',
        ...    'release/v2.0.0'
        ... ]
        >>> dict(_create_available_version_dict(available_tags))
        {'release/': [(Version(major=1, minor=2, patch=3, prerelease=None, build=None), 'release/v1.2.3'),
                      (Version(major=2, minor=0, patch=0, prerelease=None, build=None), 'release/v2.0.0')]}
    """
    parsed_tags: Dict[str, List[Tuple[Version, str]]] = defaultdict(list)
    for available_tag in available_tags:
        prefix, version, _ = coerce(available_tag)
        if version:
            parsed_tags[prefix] += [(version, available_tag)]
    return parsed_tags


if __name__ == "__main__":
    import doctest

    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
