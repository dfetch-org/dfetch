"""Version of a project."""

from typing import Any, NamedTuple


class Version(NamedTuple):
    """Version of a VCS."""

    tag: str = ""
    branch: str = ""
    revision: str = ""

    def __eq__(self, other: Any) -> bool:
        """Check if two versions can be considered as equal."""
        return other and any(
            [
                (self.tag and self.tag == other.tag),
                (self.branch == other.branch) and (self.revision == other.revision),
            ]
        )

    def __repr__(self) -> str:
        """Get the string representing this version."""
        if self.tag:
            return self.tag

        return " - ".join(filter(None, [self.branch, self.revision]))
