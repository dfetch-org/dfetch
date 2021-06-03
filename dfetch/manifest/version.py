"""Version of a project."""

from typing import Any, NamedTuple


class Version(NamedTuple):
    """Version of a project.

    In DFetch a version consists of a tag, branch or revision.
    A tag has precedence over branches/revisions.
    """

    tag: str = ""
    branch: str = ""
    revision: str = ""

    def __eq__(self, other: Any) -> bool:
        """Check if two versions can be considered as equal."""
        if not other:
            return False

        if self.tag or other.tag:
            return bool(self.tag == other.tag)

        return bool(self.branch == other.branch and self.revision == other.revision)

    def __repr__(self) -> str:
        """Get the string representing this version."""
        if self.tag:
            return self.tag

        return " - ".join(filter(None, [self.branch.strip(), self.revision]))
