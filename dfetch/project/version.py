"""Version of a project."""

from typing import NamedTuple


class Version(NamedTuple):
    """Version of a VCS."""

    tag: str = ""
    branch: str = ""
    revision: str = ""

    def __repr__(self) -> str:
        """Get the string representing this version."""
        if self.tag:
            return self.tag
        return "-".join([self.branch, self.revision])
