"""Test the PURL creation."""

import pytest

from dfetch.util.purl import remote_url_to_purl


@pytest.mark.parametrize(
    "url,expected",
    [
        # GitHub
        ("https://github.com/dfetch-org/dfetch", "pkg:github/dfetch-org/dfetch"),
        ("git+https://github.com/dfetch-org/dfetch", "pkg:github/dfetch-org/dfetch"),
        ("https://github.com/dfetch-org/dfetch.git", "pkg:github/dfetch-org/dfetch"),
        ("git@github.com:dfetch-org/dfetch.git", "pkg:github/dfetch-org/dfetch"),
        ("ssh://github.com/dfetch-org/dfetch.git", "pkg:github/dfetch-org/dfetch"),
        ("ssh://git@github.com/dfetch-org/dfetch.git", "pkg:github/dfetch-org/dfetch"),
        (
            "ssh://git@github.com:22/dfetch-org/dfetch.git",
            "pkg:github/dfetch-org/dfetch",
        ),
        ("git+ssh://github.com/dfetch-org/dfetch.git", "pkg:github/dfetch-org/dfetch"),
        # Bitbucket
        ("https://bitbucket.org/team/repo.git", "pkg:bitbucket/team/repo"),
        ("https://bitbucket.org/team/repo", "pkg:bitbucket/team/repo"),
        ("git@bitbucket.org:team/repo.git", "pkg:bitbucket/team/repo"),
        ("ssh://git@bitbucket.org/team/repo.git", "pkg:bitbucket/team/repo"),
        ("ssh://git@bitbucket.org:22/team/repo.git", "pkg:bitbucket/team/repo"),
        # SVN
        (
            "svn://svn.example.com/team/repo",
            "pkg:generic/example/team/repo?vcs_url=svn://svn.example.com/team/repo",
        ),
        (
            "svn://svn.example.co.uk/team/repo",
            "pkg:generic/example/team/repo?vcs_url=svn://svn.example.co.uk/team/repo",
        ),
        (
            "svn+ssh://svn.example.com/team/repo",
            "pkg:generic/example/team/repo?vcs_url=svn%2Bssh://svn.example.com/team/repo",
        ),
        # GitLab
        (
            "https://gitlab.com/group/project.git",
            "pkg:generic/group/project?vcs_url=https://gitlab.com/group/project.git",
        ),
        (
            "https://gitlab.com/group/project",
            "pkg:generic/group/project?vcs_url=https://gitlab.com/group/project",
        ),
        (
            "git@gitlab.com:group/project.git",
            "pkg:generic/group/project?vcs_url=ssh://git%40gitlab.com/group/project.git",
        ),
        (
            "git+ssh://gitlab.com/group/project.git",
            "pkg:generic/group/project?vcs_url=git%2Bssh://gitlab.com/group/project.git",
        ),
        # Gitea
        (
            "https://gitea.example.com/org/repo.git",
            "pkg:generic/example/org/repo?vcs_url=https://gitea.example.com/org/repo.git",
        ),
        (
            "https://gitea.example.com/org/repo",
            "pkg:generic/example/org/repo?vcs_url=https://gitea.example.com/org/repo",
        ),
        # General VCS
        (
            "https://vcs.example.com/org/repo.git",
            "pkg:generic/example/org/repo?vcs_url=https://vcs.example.com/org/repo.git",
        ),
        (
            "git@vcs.example.com:org/repo.git",
            "pkg:generic/example/org/repo?vcs_url=ssh://git%40vcs.example.com/org/repo.git",
        ),
        (
            "https://unknown.org/namespace/name.git",
            "pkg:generic/unknown/namespace/name?vcs_url=https://unknown.org/namespace/name.git",
        ),
        (
            "git@unknown.org:namespace/name.git",
            "pkg:generic/unknown/namespace/name?vcs_url=ssh://git%40unknown.org/namespace/name.git",
        ),
        (
            "ssh://git@git.mycompany.eu/org/repo",
            "pkg:generic/mycompany/org/repo?vcs_url=ssh://git%40git.mycompany.eu/org/repo",
        ),
        (
            "ssh://git@git.mycompany.eu/mycompany/group/repo",
            "pkg:generic/mycompany/mycompany/group/repo?vcs_url=ssh://git%40git.mycompany.eu/mycompany/group/repo",
        ),
        (
            "svn://svn.mycompany.local/org/repo",
            "pkg:generic/mycompany/org/repo?vcs_url=svn://svn.mycompany.local/org/repo",
        ),
        (
            "svn://svn.mycompany.local/svn/org/repo",
            "pkg:generic/mycompany/org/repo?vcs_url=svn://svn.mycompany.local/svn/org/repo",
        ),
        (
            "svn://svn.code.sf.net/p/tortoisesvn/code",
            "pkg:generic/tortoisesvn/code?vcs_url=svn://svn.code.sf.net/p/tortoisesvn/code",
        ),
        (
            "https://vcs.example.com/org/repo",
            "pkg:generic/example/org/repo?vcs_url=https://vcs.example.com/org/repo",
        ),
        (
            "https://vcs.example.co.uk/org/repo",
            "pkg:generic/example/org/repo?vcs_url=https://vcs.example.co.uk/org/repo",
        ),
        (
            "git://git.git.savannah.gnu.org/automake.git",
            "pkg:generic/automake?vcs_url=git://git.git.savannah.gnu.org/automake.git",
        ),
    ],
)
def test_remote_url_to_purl(url, expected):
    purl = remote_url_to_purl(url)
    if expected is None:
        assert purl is None
    else:
        assert str(purl) == expected
