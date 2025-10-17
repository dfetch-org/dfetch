"""Module to convert remote URLs to valid Package URLs (PURLs).

Supports: GitHub, Bitbucket, SVN, SSH paths, and more.
"""

import re
from typing import Optional
from urllib.parse import urlparse

from packageurl import PackageURL
from tldextract import TLDExtract

# Although tldextract can fetch the latest suffix list, we don't want that here
NO_FETCH_EXTRACT = TLDExtract(suffix_list_urls=(), extra_suffixes=("local",))

# Matches SSH-style Git URLs like:
#   git@gitlab.com:org/repo.git
#   git+ssh://git@github.com/org/repo
#   ssh://git@git.mycompany.eu/org/repo
#
SSH_REGEX = re.compile(
    r"^(?:git@|git\+ssh://git@|ssh://)(?P<host>[^/:]+)[:/](?P<path>.+?)(?:\.git)?$",
    re.IGNORECASE,
)

GITHUB_REGEX = re.compile(
    r".*github\.com(?::\d+)?[:/](?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    re.IGNORECASE,
)

BITBUCKET_REGEX = re.compile(
    r".*bitbucket\.org(?::\d+)?[:/](?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    re.IGNORECASE,
)

# These domains have no specific Purl type, but adding the domain to the purl doesn't add any value
EXCLUDED_DOMAINS = ["gitlab", "gitea", "gitee", "sf", "gnu"]

# Name given to a package or group if it is not extractable from the URL
DEFAULT_NAME = "unknown"


def _namespace_and_name_from_domain_and_path(domain: str, path: str) -> tuple[str, str]:
    """Split the full path to a name and namespace."""
    domain = NO_FETCH_EXTRACT(domain).domain
    parts: list[str] = [domain] if domain not in EXCLUDED_DOMAINS else []

    if path:
        parts.extend(path.split("/"))
    name = parts[-1] if parts else DEFAULT_NAME
    namespace = "/".join(parts[:-1])

    return namespace, name


def _known_purl_types(
    remote_url: str, version: Optional[str] = None, subpath: Optional[str] = None
) -> Optional[PackageURL]:
    match = GITHUB_REGEX.match(remote_url)
    if match:
        return PackageURL(
            type="github",
            namespace=match.group("org"),
            name=match.group("repo"),
            version=version,
            subpath=subpath,
        )

    match = BITBUCKET_REGEX.match(remote_url)
    if match:
        return PackageURL(
            type="bitbucket",
            namespace=match.group("org"),
            name=match.group("repo"),
            version=version,
            subpath=subpath,
        )
    return None


def remote_url_to_purl(
    remote_url: str, version: Optional[str] = None, subpath: Optional[str] = None
) -> PackageURL:
    """Convert a remote URL to a valid PackageURL object.

    Supports GitHub, Bitbucket, SVN, SSH paths.
    Optionally specify version and subpath.
    """
    purl = _known_purl_types(remote_url, version, subpath)
    if purl:
        return purl

    parsed = urlparse(remote_url)
    path = parsed.path.lstrip("/")

    if "svn" in parsed.scheme or "svn." in parsed.netloc:
        namespace, name = _namespace_and_name_from_domain_and_path(parsed.netloc, path)
        if namespace.startswith("p/"):
            namespace = namespace[len("p/") :]
        namespace = namespace.replace("/svn/", "/")

    else:
        match = SSH_REGEX.match(remote_url)
        if match:
            namespace, name = _namespace_and_name_from_domain_and_path(
                match.group("host"),
                match.group("path"),
            )

            if not parsed.scheme:
                remote_url = f"ssh://{parsed.path.replace(':', '/')}"
        else:
            namespace, name = _namespace_and_name_from_domain_and_path(
                remote_url, path.replace(".git", "")
            )

    return PackageURL(
        type="generic",
        namespace=namespace,
        name=name,
        version=version,
        qualifiers={"vcs_url": remote_url},
        subpath=subpath,
    )
