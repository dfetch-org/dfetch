"""CMake external dependency detection.

Parses ``FetchContent_Declare`` and ``ExternalProject_Add`` calls from
``CMakeLists.txt`` and ``.cmake`` files to extract dependency information.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from dfetch.log import get_logger

logger = get_logger(__name__)

_COMMAND_RE = re.compile(
    r"(?:FetchContent_Declare|ExternalProject_Add)\s*\(",
    re.IGNORECASE,
)
_COMMENT_RE = re.compile(r"#[^\n]*")
_GIT_REPO_RE = re.compile(r"\bGIT_REPOSITORY\b\s+(\S+)", re.IGNORECASE)
_GIT_TAG_RE = re.compile(r"\bGIT_TAG\b\s+(\S+)", re.IGNORECASE)

# \bURL\b ensures URL_HASH is not matched (underscore breaks the word boundary)
_URL_RE = re.compile(r"\bURL\b\s+(?!HASH\b)(\S+)", re.IGNORECASE)


@dataclass
class CMakeExternalDependency:
    """A dependency declared via FetchContent_Declare or ExternalProject_Add."""

    name: str
    git_repository: str = ""
    git_tag: str = ""
    url: str = ""


def find_cmake_dependencies(directory: Path) -> list[CMakeExternalDependency]:
    """Find all CMake FetchContent/ExternalProject dependencies in a directory.

    Scans ``CMakeLists.txt`` and ``*.cmake`` files recursively.

    Args:
        directory: Root directory to search.

    Returns:
        List of discovered cmake external dependencies.
    """
    dependencies: list[CMakeExternalDependency] = []
    for cmake_file in _find_cmake_files(directory):
        try:
            text = cmake_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.warning(f"Could not read {cmake_file}")
            continue
        for dep in _find_dependencies_in_text(text):
            logger.info(f"Found cmake dependency '{dep.name}' in {cmake_file}")
            dependencies.append(dep)
    return dependencies


def _find_cmake_files(directory: Path) -> Iterator[Path]:
    """Yield CMakeLists.txt and .cmake files found recursively under directory."""
    yield from directory.rglob("CMakeLists.txt")
    yield from directory.rglob("*.cmake")


def _find_dependencies_in_text(text: str) -> Iterator[CMakeExternalDependency]:
    """Yield cmake external dependencies parsed from *text*."""
    cleaned = _COMMENT_RE.sub("", text)
    for match in _COMMAND_RE.finditer(cleaned):
        body = _extract_body(cleaned, match.end())
        dependency = _parse_body(body)
        if dependency is not None:
            yield dependency


def _extract_body(text: str, start: int) -> str:
    """Return the content between balanced parentheses starting at *start*.

    The character at *start* is the first character *after* the opening ``(``.
    """
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        i += 1
    return text[start : i - 1]


def _parse_body(body: str) -> CMakeExternalDependency | None:
    """Parse a cmake command body into a dependency, or ``None`` if not usable."""
    name = _extract_name(body)
    if not name:
        return None

    git_repository = _extract_value(_GIT_REPO_RE, body)
    url = _extract_value(_URL_RE, body)

    if not git_repository and not url:
        return None

    return CMakeExternalDependency(
        name=name,
        git_repository=git_repository,
        git_tag=_extract_value(_GIT_TAG_RE, body),
        url=url,
    )


def _extract_name(body: str) -> str:
    """Return the first whitespace-delimited token from *body* as the name."""
    tokens = body.split()
    return tokens[0].strip('"') if tokens else ""


def _extract_value(pattern: re.Pattern[str], text: str) -> str:
    """Return the first capture group of *pattern* in *text*, or empty string."""
    match = pattern.search(text)
    return match.group(1).strip('"') if match else ""
