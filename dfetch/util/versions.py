"""Module for handling version information from strings."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

import semver
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


def coerce(version: str) -> tuple[str, Version | None, str]:
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


def latest_tag_from_list(current_tag: str, available_tags: list[str]) -> str:
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
    available_tags: list[str],
) -> dict[str, list[tuple[Version, str]]]:
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
    parsed_tags: dict[str, list[tuple[Version, str]]] = defaultdict(list)
    for available_tag in available_tags:
        prefix, version, _ = coerce(available_tag)
        if version:
            parsed_tags[prefix] += [(version, available_tag)]
    return parsed_tags


@dataclass(frozen=True)
class VersionRef:
    """A resolved version reference: a branch name, tag, or commit SHA."""

    kind: Literal["branch", "tag", "revision"]
    value: str


def prioritise_default(branches: list[str], default: str) -> list[str]:
    """Return *branches* with *default* moved to position 0."""
    if default in branches:
        rest = [b for b in branches if b != default]
        return [default, *rest]
    return branches


def sort_tags_newest_first(tags: list[str]) -> list[str]:
    """Sort *tags* newest-semver-first; non-semver tags appended as-is."""

    def _parse_semver(tag: str) -> semver.Version | None:
        try:
            return semver.Version.parse(tag.lstrip("vV"))
        except ValueError:
            return None

    parsed = {t: _parse_semver(t) for t in tags}
    semver_tags = sorted(
        (t for t, v in parsed.items() if v is not None),
        key=lambda t: parsed[t],  # type: ignore[arg-type, return-value]
        reverse=True,
    )
    non_semver = [t for t, v in parsed.items() if v is None]
    return semver_tags + non_semver


def is_commit_sha(value: str) -> bool:
    """Return True when *value* looks like a Git commit SHA (7–40 hex chars)."""
    return bool(re.fullmatch(r"[0-9a-fA-F]{7,40}", value))


if __name__ == "__main__":
    import doctest

    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
