"""Git data types shared across the vcs and project layers."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class Submodule:
    """Information about a submodule."""

    name: str
    toplevel: str
    path: str
    sha: str
    url: str
    branch: str
    tag: str


@dataclass
class CheckoutOptions:
    """Options for checking out a specific version from a remote git repository."""

    remote: str
    version: str
    src: str | None = None
    must_keeps: Sequence[str] | None = None
    ignore: Sequence[str] | None = None
