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

from typing import Dict


class Remote:
    """A single remote entry in the manifest file."""

    def __init__(self, yamldata: Dict[str, str]) -> None:
        """Create the remote entry."""
        self._name: str = yamldata["name"]
        self._url_base: str = yamldata["url-base"]
        self._default: bool = bool(yamldata.get("default", False))

    @property
    def url(self) -> str:
        """Get the url of the remote."""
        return self._url_base

    @property
    def is_default(self) -> bool:
        """Check if this is a default remote."""
        return self._default
