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
When no version is provided the latest version of the default branch (e.g. `trunk`, `master`) of
a project will be chosen. Since we want more control on what project is retrieved the
``revision:``, ``branch:`` and ``tag:`` attributes can help.
Below manifest will download tag ``v1.13`` of ``mymodule``.

The ``tag:`` attribute takes priority over ``revision:`` and ``branch:``.
With ``revision:`` a specific commit (git) or revision (svn) is retrieved. For git,
revisions must be complete 40 character long SHA-hashes.
For git if only a revision is provided and no branch, *DFetch* cannot determine if there are updates,
so it will assume you require that specific version.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule
           tag: v1.13

         - name: myothermodule
           revision: dcc92d0ab6c4ce022162a23566d44f673251eee4

.. note:: For svn a `standard layout`_ is advised. Meaning the top of the repository has a ``trunk``,
          ``branches`` and ``tags`` folder. If this is not the case, you can indicate this by using
          ``branch: ' '``.

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

If no ``dst:`` is provided, *DFetch* will use the project name as relative path.
The ``dst:`` must be in the same folder or a folder below the manifest and must be
unique.

.. scenario-include:: ../features/fetch-checks-destination.feature

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
limit the checkout to only that folder. *Dfetch* will retain any license file in the
root of the repository.

.. scenario-include:: ../features/keep-license-in-project.feature

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

It is also possible to use an ``*`` to match only certain files with the ``src`` tag.
The following manifest will only checkout files in folder ``src`` with the ``*.h`` extension.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: github
          url-base: https://github.com/

        projects:
        - name: cpputest
          src: src/*.h
          repo-path: cpputest/cpputest

.. scenario-include:: ../features/fetch-file-pattern-git.feature

Ignore
######
In larger projects or mono-repo's it is often desirable to ignore certain files such as Tests
*Dfetch* makes this possible through the ``ignore:`` attribute.

For instance if you are not interested in the ``tests`` folder of ``cpputest`` you can
limit the checkout to ignore that folder. *Dfetch* will retain any license file in the
root of the repository.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: github
          url-base: https://github.com/

        projects:
        - name: cpputest
          ignore:
          - tests
          repo-path: cpputest/cpputest

.. note:: For projects using ``src:`` field, the ignore list will be relative to that folder.
          And the ignores will be applied *after* the ``src:`` pattern was applied.
          License files will never be excluded, since you likely shouldn't be doing that.

.. scenario-include:: ../features/fetch-with-ignore-git.feature

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

Patch
#####
*DFetch* promotes upstreaming changes, but also allows local changes. These changes can be managed with a local patch
file. *DFetch* will apply the patch file every time a new upstream version is fetched. The patch file can be specified
with the ``patch:`` attribute.

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
          patch: local_changes.patch

The patch can be generated using the *Dfetch* :ref:`Diff` command.
Alternately the patch can be generated manually as such. Note that it should be *relative*.

.. code-block:: sh

    # For git repo's
    git diff --relative=path/to/project HEAD > my_patch.patch

    # For svn repo's
    svn diff -r HEAD path/to/my_project > my_patch.patch

For more details see the `git-diff`_ or `svn-diff`_ documentation.

.. _`git-diff`: https://git-scm.com/docs/git-diff
.. _`svn-diff`: http://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.diff.html

.. scenario-include:: ../features/diff-in-git.feature

"""

import copy
from typing import Dict, Optional, Sequence, Union

from typing_extensions import TypedDict

from dfetch.manifest.remote import Remote
from dfetch.manifest.version import Version

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
        "tag": str,
        "repo-path": str,
        "vcs": str,
        "ignore": Sequence[str],
        "default_remote": str,
    },
    total=False,
)


class ProjectEntry:  # pylint: disable=too-many-instance-attributes
    """A single Project entry in the manifest file."""

    def __init__(self, kwargs: ProjectEntryDict) -> None:
        """Create the project entry."""
        if "name" not in kwargs:
            raise RuntimeError("Name missing from Project!")
        self._name: str = kwargs["name"]
        self._revision: str = kwargs.get("revision", "")

        self._remote: str = kwargs.get("remote", "")
        self._remote_obj: Optional[Remote] = None
        self._src: str = kwargs.get("src", "")  # noqa
        self._dst: str = kwargs.get("dst", self._name)
        self._url: str = kwargs.get("url", "")
        self._patch: str = kwargs.get("patch", "")  # noqa
        self._repo_path: str = kwargs.get("repo-path", "")
        self._branch: str = kwargs.get("branch", "")
        self._tag: str = kwargs.get("tag", "")
        self._vcs: str = kwargs.get("vcs", "")
        self._ignore: Sequence[str] = kwargs.get("ignore", [])

        if not self._remote and not self._url:
            self._remote = kwargs.get("default_remote", "")

    @classmethod
    def from_yaml(
        cls,
        yamldata: Union[Dict[str, str], ProjectEntryDict],
        default_remote: str = "",
    ) -> "ProjectEntry":
        """Create a Project Entry from yaml data.

        Returns:
            ProjectEntry:  An immutable ProjectEntry
        """
        kwargs: ProjectEntryDict = {}
        for key in ProjectEntryDict.__annotations__.keys():  # pylint: disable=no-member
            try:
                kwargs[str(key)] = yamldata[key]  # type: ignore
            except KeyError:
                pass
        kwargs["default_remote"] = default_remote
        return cls(kwargs)

    @classmethod
    def copy(cls, other: "ProjectEntry") -> "ProjectEntry":
        """Create a Project Entry copy from a Project Entry."""
        return copy.copy(other)

    def set_remote(self, remote: Remote) -> None:
        """Set the remote."""
        self._remote_obj = remote
        self._remote = remote.name
        if self._url.startswith(remote.url):
            self._repo_path = self._url.replace(remote.url, "").strip("/")
            self._url = ""

    @property
    def version(self) -> Version:
        """Get the version of the project."""
        if self._tag:
            return Version(tag=self._tag)

        return Version(branch=self._branch, revision=self._revision)

    @version.setter
    def version(self, version: Version) -> None:
        """Set the version of the project."""
        if version.tag:
            self._tag = version.tag
        else:
            self._branch = version.branch
            self._revision = version.revision

    @property
    def remote_url(self) -> str:
        """Get the remote url of the project."""
        if self._url:
            return self._url
        if self._remote_obj:
            urls = [self._remote_obj.url.strip("/"), self._repo_path]
            return "/".join(urls).strip("/")
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
    def patch(self) -> str:
        """Get the patch that should be applied."""
        return self._patch

    @property
    def branch(self) -> str:
        """Get the branch that should be fetched."""
        return self._branch

    @property
    def tag(self) -> str:
        """Get the tag that should be fetched."""
        return self._tag

    @property
    def revision(self) -> str:
        """Get the revision that should be fetched."""
        return self._revision

    @property
    def vcs(self) -> str:
        """Get the type of version control system."""
        return self._vcs

    @property
    def ignore(self) -> Sequence[str]:
        """Get the list of files/folders to ignore from this project (relative to src)."""
        return self._ignore

    def __repr__(self) -> str:
        """Get a string representation of this project entry."""
        version = (
            f"{self.branch} {self.revision}".strip()
            if (self.branch or self.revision)
            else "latest"
        )
        return f"{self.name:20s} {version} {self.remote_url} {self.destination}"

    def as_recommendation(self) -> "ProjectEntry":
        """Get a copy that can be used as recommendation."""
        recommendation = self.copy(self)
        recommendation._dst = ""  # pylint: disable=protected-access
        recommendation._patch = ""  # pylint: disable=protected-access
        recommendation._url = self.remote_url  # pylint: disable=protected-access
        recommendation._remote = ""  # pylint: disable=protected-access
        recommendation._remote_obj = None  # pylint: disable=protected-access
        recommendation._repo_path = ""  # pylint: disable=protected-access
        return recommendation

    def as_yaml(self) -> Dict[str, str]:
        """Get this project as yaml dictionary."""
        yamldata = {
            "name": self._name,
            "revision": self._revision,
            "remote": self._remote,
            "src": self._src,
            "dst": self._dst if self._dst != self._name else None,
            "url": self._url,
            "patch": self._patch,
            "branch": self._branch,
            "tag": self._tag,
            "repo-path": self._repo_path,
            "vcs": self._vcs,
        }

        return {k: v for k, v in yamldata.items() if v}
