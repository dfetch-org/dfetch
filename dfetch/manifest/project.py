"""Projects are a specific repository or sources to download from a remote location.

In its most basic form a project only has a ``name:``. This would make `Dfetch`
retrieve the mymodule project from the only remote listed (`mycompany-git-modules`)
and place it in a folder ``mymodule`` in the same folder as the manifest.

A project name **must** be unique and each manifest must have at least one project.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule

Revision/Branch/Tag
###################
Since we want more control on what project is retrieved the ``revision:`` and ``branch:``
attributes can help. Below manifest will download tag ``v1.13`` of ``mymodule``.

With ``revision:`` a specific commit (git) or revision (svn) is retrieved.  For git,
revisions must be complete 40 character long SHA-hashes.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule
           branch: v1.13

         - name: myothermodule
           revision: dcc92d0ab6c4ce022162a23566d44f673251eee4

For svn a `standard layout`_ is assumed. Meaning the top of the repository has a ``trunk``,
``branches`` and ``tags`` folder.

.. _`standard layout`:
    https://stackoverflow.com/questions/3859009/how-to-create-a-subversion-repository-with-standard-layout

Destination
###########
To control where the project is placed, the ``dst:`` attribute can be used. Below manifest
will place ``mymodule`` at the relative path listed by ``dst:`` (relative to the manifest location).

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule
           dst: external/mymodule

Repo-path
#########
When working with remotes_ by default *Dfetch* will take the ``url-base`` of the remote
and concatenate that with the name of the project. Sometimes you want more control
of the name, you can use the ``repo-path:`` attribute to list it explicitly.

For instance, below example will look for the remote project at ``<url-base>:<repo-path>``,
which would be ``https://github.com/cpputest/cpputest``.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: github
          url-base: https://github.com/

        projects:
        - name: cpputest
          repo-path: cpputest/cpputest

Source
######
In larger projects or mono-repo's it is often desirable to retrieve only a subfolder
of an external project. *Dfetch* makes this possible through the ``src:`` attribute.

For instance if you are only interested in the ``src`` folder of ``cpputest`` you can
limit the checkout to only that folder.

.. note::
    *Dfetch* (currently) will only checkout that folder, it could be that you are not compliant
    with a software license. Please check the original project's license and also comply with that.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: github
          url-base: https://github.com/

        projects:
        - name: cpputest
          src: src
          repo-path: cpputest/cpputest

VCS type
########
*DFetch* does it best to find out what type of version control system (vcs) the remote url is,
but sometimes both is possible. For example, GitHub provides an `svn and git interface at
the same url`_.

.. _`svn and git interface at the same url`:
   https://docs.github.com/en/github/importing-your-projects-to-github/support-for-subversion-clients

To provide you an option to explicitly state the vcs, the ``vcs:`` attribute was introduced. In the below example
the same project is fetched as SVN and as Git repository. *Dfetch* will default to the latest revision
from trunk for svn and master from git.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: github
          url-base: https://github.com/

        projects:
        - name: cpputest
          vcs: git
          repo-path: cpputest/cpputest

        - name: cpputestSVN
          vcs: svn
          repo-path: cpputest/cpputest

"""
import copy
from typing import Dict, Optional, Union

from typing_extensions import TypedDict

from dfetch.manifest.remote import Remote

ProjectEntryDict = TypedDict(
    "ProjectEntryDict",
    {
        "name": str,
        "revision": str,
        "remote": str,
        "src": str,
        "dst": str,
        "url": str,
        "patch": str,
        "repo": str,
        "branch": str,
        "repo-path": str,
        "vcs": str,
        "default_remote": Optional[Remote],
    },
    total=False,
)


class ProjectEntry:  # pylint: disable=too-many-instance-attributes
    """A single Project entry in the manifest file."""

    def __init__(self, kwargs: ProjectEntryDict) -> None:
        """Create the project entry."""
        self._name: str = kwargs["name"]
        self._revision: str = kwargs.get("revision", "")

        self._remote: str = kwargs.get("remote", "")
        self._remote_obj: Optional[Remote] = kwargs.get("default_remote", None)
        self._src: str = kwargs.get("src", "")  # noqa
        self._dst: str = kwargs.get("dst", self._name)
        self._url: str = kwargs.get("url", "")
        self._patch: str = kwargs.get("patch", "")  # noqa
        self._repo_path: str = kwargs.get("repo-path", "")
        self._branch: str = kwargs.get("branch", "")
        self._vcs: str = kwargs.get("vcs", "")

    @classmethod
    def from_yaml(
        cls,
        yamldata: Union[Dict[str, str], ProjectEntryDict],
        default_remote: Optional[Remote] = None,
    ) -> "ProjectEntry":
        """Create a Project Entry from yaml data.

        Returns:
            ProjectEntry:  An immutable ProjectEntry
        """
        kwargs: ProjectEntryDict = {}
        for key in ProjectEntryDict.__annotations__.keys():
            try:
                kwargs[str(key)] = yamldata[key]  # type: ignore
            except KeyError:
                pass
        kwargs["default_remote"] = default_remote
        return cls(kwargs)

    @classmethod
    def copy(
        cls, other: "ProjectEntry", default_remote: Optional[Remote] = None
    ) -> "ProjectEntry":
        """Create a Project Entry copy from a Project Entry."""
        # pylint: disable=protected-access
        the_copy = copy.copy(other)
        if not the_copy._remote_obj:
            the_copy._remote_obj = default_remote
        return the_copy

    def set_remote(self, remote: Remote) -> None:
        """Set the remote."""
        self._remote_obj = remote
        self._remote = remote.name
        if self._url.startswith(remote.url):
            self._repo_path = self._url.replace(remote.url, "").strip("/")
            self._url = ""

    @property
    def remote_url(self) -> str:
        """Get the remote url of the project."""
        if self._url:
            return self._url
        if self._remote_obj:
            return "/".join(
                self._remote_obj.url.strip("/").split("/") + self._repo_path.split("/")
            )
        return ""

    @property
    def remote(self) -> str:
        """Get the url."""
        return self._remote

    @property
    def name(self) -> str:
        """Get the name of the project."""
        return self._name

    @property
    def source(self) -> str:
        """Get the path within the remote project."""
        return self._src

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

    @property
    def vcs(self) -> str:
        """Get the type of version control system."""
        return self._vcs

    def __repr__(self) -> str:
        """Get a string representation of this project entry."""
        version = (
            f"{self.branch} {self.revision}".strip()
            if (self.branch or self.revision)
            else "latest"
        )
        return f"{self.name:20s} {version} {self.remote_url} {self.destination}"

    def as_yaml(self) -> Dict[str, str]:
        """Get this project as yaml dictionary."""
        yamldata = {
            "name": self._name,
            "revision": self._revision,
            "remote": self._remote,
            "src": self._src,
            "dst": self._dst,
            "url": self._url,
            "patch": self._patch,
            "branch": self._branch,
            "repo-path": self._repo_path,
            "vcs": self._vcs,
        }

        return {k: v for k, v in yamldata.items() if v}
