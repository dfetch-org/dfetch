"""Remotes are the external repository where the code should be retrieved from.

If only one remote is added this is assumed to be the default.
If multiple remotes are listed ``default:`` can be explicitly specified.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/
          default: true
        - name: github
          url-base: https://github.com/
"""

from typing import Dict, Optional, Union

from typing_extensions import TypedDict

_MandatoryRemoteDict = TypedDict("_MandatoryRemoteDict", {"name": str, "url-base": str})


class RemoteDict(_MandatoryRemoteDict, total=False):
    """Class representing data types of Remote class construction."""

    default: Optional[bool]


class Remote:
    """A single remote entry in the manifest file."""

    def __init__(self, kwargs: RemoteDict) -> None:
        """Create the remote entry."""
        self._name: str = kwargs["name"]
        self._url_base: str = kwargs["url-base"]
        self._default: bool = bool(kwargs.get("default", False))

    @classmethod
    def from_yaml(cls, yamldata: Union[Dict[str, str], RemoteDict]) -> "Remote":
        """Create a remote entry in the manifest from yaml data.

        Returns:
            Remote: Entry containing the immutable remote entry
        """
        return cls(
            {
                "name": yamldata["name"],
                "url-base": yamldata["url-base"],
                "default": bool(yamldata.get("default", False)),
            }
        )

    @classmethod
    def copy(cls, other: "Remote") -> "Remote":
        """Generate a new remote entry in the manifest from another.

        Args:
            other (Remote): Other Remote to copy the values from

        Returns:
            Remote: Entry containing the immutable remote entry
        """
        return cls(
            {"name": other.name, "url-base": other.url, "default": other.is_default}
        )

    @property
    def name(self) -> str:
        """Get the name of the remote."""
        return self._name

    @property
    def url(self) -> str:
        """Get the url of the remote."""
        return self._url_base

    @property
    def is_default(self) -> bool:
        """Check if this is a default remote."""
        return self._default

    def __repr__(self) -> str:
        """Get a string representation of this remote."""
        return str(self.as_yaml())

    def as_yaml(self) -> RemoteDict:
        """Get this remote as yaml data."""
        yamldata: RemoteDict = {"name": self._name, "url-base": self._url_base}

        if self.is_default:
            yamldata["default"] = True

        return yamldata
