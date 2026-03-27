"""Detector registry and abstract base class for ``dfetch import --detect``.

A *detector* knows how to read a third-party dependency declaration format
(e.g. CMake FetchContent, Conan, pip ``requirements.txt``) and convert the
declarations it finds into dfetch
:class:`~dfetch.manifest.project.ProjectEntry` objects.

Adding a new detector
=====================

1. Create a module ``dfetch/commands/detectors/<yourformat>.py``.
2. Define a class that inherits from :class:`Detector` and sets a unique,
   lower-case :attr:`Detector.name` (e.g. ``"conan"``).  That name is the
   keyword users supply to ``--detect``.
3. Implement :meth:`Detector.detect`.
4. Decorate the class with ``@register``.
5. Import the new module at the bottom of
   ``dfetch/commands/detectors/__init__.py`` so it is registered
   automatically when the package is first imported.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from dfetch.manifest.project import ProjectEntry


class Detector(ABC):
    """Convert a dependency-declaration format into dfetch project entries.

    Attributes:
        name: Lower-case CLI keyword passed to ``--detect`` (e.g. ``"cmake"``).
        supports_clean_sources: ``True`` once :meth:`clean_sources` is
            overridden; defaults to ``False``.
    """

    name: ClassVar[str] = ""
    supports_clean_sources: ClassVar[bool] = False

    @classmethod
    @abstractmethod
    def detect(cls, directory: Path) -> Sequence[ProjectEntry]:
        """Return project entries discovered under *directory*.

        Args:
            directory: Root directory to search recursively.

        Returns:
            Discovered project entries (may be empty).
        """

    @classmethod
    def clean_sources(cls, directory: Path) -> None:
        """Comment out or remove detected declarations from source files.

        Override this method **and** set ``supports_clean_sources = True``
        to support ``--clean-sources`` for this detector.

        Args:
            directory: Root directory whose source files should be modified.

        Raises:
            NotImplementedError: Always, until overridden by a subclass.
        """
        raise NotImplementedError(
            f"--clean-sources is not yet supported for detector '{cls.name}'"
        )


_REGISTRY: dict[str, type[Detector]] = {}


def register(cls: type[Detector]) -> type[Detector]:
    """Register *cls* and return it unchanged (use as a class decorator).

    Example::

        @register
        class MyDetector(Detector):
            name = "myformat"
            ...

    Args:
        cls: A :class:`Detector` subclass with a non-empty ``name``.

    Returns:
        The unmodified class.

    Raises:
        ValueError: If ``cls.name`` is empty.
    """
    if not cls.name:
        raise ValueError(
            f"{cls.__name__} must define a non-empty 'name' class variable"
        )
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> type[Detector]:
    """Return the registered detector class for *name*.

    Args:
        name: The :attr:`Detector.name` to look up.

    Returns:
        The matching detector class.

    Raises:
        KeyError: If *name* is not registered.
    """
    return _REGISTRY[name]


def names() -> list[str]:
    """Return a sorted list of all registered detector names.

    Returns:
        Sorted detector names.
    """
    return sorted(_REGISTRY)
