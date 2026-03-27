"""CMake FetchContent / ExternalProject detector for ``dfetch import --detect cmake``.

Wraps the low-level CMake parser in :mod:`dfetch.vcs.cmake` and converts the
found declarations to :class:`~dfetch.manifest.project.ProjectEntry` objects.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from dfetch.commands.detectors._base import Detector, register
from dfetch.manifest.project import ProjectEntry
from dfetch.vcs.cmake import CMakeExternalDependency, find_cmake_dependencies

_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


@register
class CmakeDetector(Detector):
    """Detect CMake FetchContent_Declare and ExternalProject_Add dependencies.

    Scans all ``CMakeLists.txt`` and ``*.cmake`` files in a directory tree
    and converts the found declarations to dfetch project entries.

    Attributes:
        name: ``"cmake"`` — the keyword passed to ``--detect cmake``.
        supports_clean_sources: Not yet implemented; always ``False``.
    """

    name = "cmake"

    @classmethod
    def detect(cls, directory: Path) -> Sequence[ProjectEntry]:
        """Return project entries from CMake FetchContent/ExternalProject declarations.

        Args:
            directory: Root directory to search recursively.

        Returns:
            Sequence of project entries found in cmake files.
        """
        entries: list[ProjectEntry] = []
        for dep in find_cmake_dependencies(directory):
            entry = _dep_to_entry(dep)
            if entry is not None:
                entries.append(entry)
        return entries


def _dep_to_entry(dep: CMakeExternalDependency) -> ProjectEntry | None:
    """Convert a cmake external dependency to a ProjectEntry.

    Args:
        dep: The cmake dependency to convert.

    Returns:
        A ProjectEntry, or ``None`` when the dependency has no usable URL.
    """
    url = dep.git_repository or dep.url
    if not url:
        return None
    tag, revision = _classify_git_ref(dep.git_tag)
    return ProjectEntry(
        {"name": dep.name, "url": url, "tag": tag, "revision": revision}
    )


def _classify_git_ref(ref: str) -> tuple[str, str]:
    """Classify a git ref string into ``(tag, revision)``.

    A 40-character hexadecimal string is treated as a commit SHA
    (``revision``); everything else is treated as a tag or branch name
    (``tag``).

    Args:
        ref: Git ref string to classify.

    Returns:
        ``(tag, revision)`` where exactly one value is non-empty, unless
        *ref* is empty — then both are empty.
    """
    if _SHA_RE.match(ref):
        return "", ref
    return ref, ""
