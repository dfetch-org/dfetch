"""Type aliases for the terminal package."""

from collections.abc import Callable

LsFunction = Callable[[str], list[tuple[str, bool]]]
