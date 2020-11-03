"""Projects are specific repository or sources to download from a remote location.

In its most basic form a project only has a 'name:'. This would make `Dfetch`
retrieve the mymodule project from the only remote listed (`mycompany-git-modules`)
and place it in a folder ``mymodule`` in the same folder as the manifest.

.. note:: A project name *must* be unique.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule

Destination and revision
########################
Since we want more control on what project is retrieved and where it is placed
the ``revision:``, ``branch:`` and ``dst:`` attributes can help. Below manifest
will download tag ``v1.13`` of the mymodule and place it in the path listed by ``dst:``.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule
           branch: v1.13
           dst: external/mymodule

We can also list multiple projects.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule
           branch: v1.13
           dst: external/mymodule

         - name: myothermodule
           revision: bea84ba8f
           dst: external/myothermodule

"""

from typing import Dict

from dfetch.manifest.remote import Remote


class ProjectEntry:  # pylint: disable=too-many-instance-attributes
    """A single Project entry in the manifest file."""

    def __init__(self, yamldata: Dict[str, str], default_remote: Remote) -> None:
        """Create the project entry."""
        self._name: str = yamldata["name"]
        self._revision: str = yamldata.get("revision", "")

        self._remote: str = yamldata.get("remote", "")
        self._remote_obj: Remote = default_remote
        self._src: str = yamldata.get("src", "")  # noqa
        self._dst: str = yamldata.get("dst", ".")
        self._url: str = yamldata.get("url", "")
        self._patch: str = yamldata.get("patch", "")  # noqa
        self._repo_path: str = yamldata.get("repo-path", "")
        self._branch: str = yamldata.get("branch", "")

    def set_remote(self, remote: Remote) -> None:
        """Set the remote."""
        self._remote_obj = remote

    @property
    def remote_url(self) -> str:
        """Get the remote url of the project."""
        return self._url or "/".join(
            self._remote_obj.url.strip("/").split("/") + self._repo_path.split("/")
        )

    @property
    def remote(self) -> str:
        """Get the url."""
        return self._remote

    @property
    def name(self) -> str:
        """Get the name of the project."""
        return self._name

    @property
    def destination(self) -> str:
        """Get the local path the project should be copied to."""
        return self._dst

    @property
    def branch(self) -> str:
        """Get the branch that should be fetched."""
        return self._branch

    @property
    def revision(self) -> str:
        """Get the revision that should be fetched."""
        return self._revision

    def __repr__(self) -> str:
        """Get a string representation of this project entry."""
        version = (
            f"{self.branch} {self.revision}".strip()
            if (self.branch or self.revision)
            else "latest"
        )
        return f"{self.name:20s} [{version}]"
