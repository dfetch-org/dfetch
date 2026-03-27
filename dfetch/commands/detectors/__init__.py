"""Project-source detectors for ``dfetch import --detect``.

Each detector converts a third-party dependency declaration format into
dfetch :class:`~dfetch.manifest.project.ProjectEntry` objects.

Built-in detectors
==================

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - ``--detect`` keyword
     - Description
   * - ``cmake``
     - CMake ``FetchContent_Declare`` and ``ExternalProject_Add`` calls
       found in ``CMakeLists.txt`` and ``*.cmake`` files.

See :mod:`dfetch.commands.detectors._base` for the extension API.
"""

# Re-export the public API so callers need only import from this package.
from dfetch.commands.detectors._base import Detector, get, names, register

# ---------------------------------------------------------------------------
# Register built-in detectors.
# Each import below triggers the @register decorator inside that module.
# To add a new built-in detector, append an import here.
# ---------------------------------------------------------------------------
from dfetch.commands.detectors.cmake import CmakeDetector

__all__ = [
    "CmakeDetector",
    "Detector",
    "get",
    "names",
    "register",
]
