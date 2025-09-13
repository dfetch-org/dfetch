"""Module to convert remote URLs to valid Package URLs (PURLs).

Supports: GitHub, Bitbucket, SVN, SSH paths, and more.
"""

import re
from typing import Callable, List, Optional
from urllib.parse import urlparse

from packageurl import PackageURL
from tldextract import TLDExtract

HandlerType = Callable[[str, str, Optional[str], Optional[str]], Optional[PackageURL]]

NO_FETCH_EXTRACT = TLDExtract(suffix_list_urls=())
SSH_REGEX = re.compile(
    r"^(?:git@|git\+ssh://git@)(?P<host>[^/:]+)[:/](?P<path>.+?)(?:\.git)?$"
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
EXCLUDED_DOMAINS = ["gitlab", "gitea", "gitee"]

# Name given to a package or group if it is not extractable from the URL
DEFAULT_NAME = "unknown"


def _handle_github(
    remote_url: str,
    _: str,
    version: Optional[str],
    subpath: Optional[str],
) -> Optional[PackageURL]:
    """Handler for GitHub URLs."""
    match = GITHUB_REGEX.match(remote_url)
    if match:
        return PackageURL(
            type="github",
            namespace=match.group("org"),
            name=match.group("repo"),
            version=version,
            subpath=subpath,
        )
    return None


def _handle_bitbucket(
    remote_url: str,
    _: str,
    version: Optional[str],
    subpath: Optional[str],
) -> Optional[PackageURL]:
    """Handler for Bitbucket URLs."""
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


def _handle_svn(
    remote_url: str,
    path: str,
    version: Optional[str],
    subpath: Optional[str],
) -> Optional[PackageURL]:
    """Handler for SVN URLs."""
    parsed = urlparse(remote_url)
    if "svn" in parsed.scheme or "svn." in parsed.netloc:
        domain = NO_FETCH_EXTRACT(parsed.netloc).domain

        parts: list[str] = [domain]
        if path:
            parts.extend(path.split("/"))
        name = parts[-1] if parts else DEFAULT_NAME
        namespace = "/".join(parts[:-1])

        return PackageURL(
            type="generic",
            namespace=namespace,
            name=name,
            version=version,
            qualifiers={"vcs_url": remote_url},
            subpath=subpath,
        )
    return None


def _handle_ssh(
    remote_url: str,
    path: str,
    version: Optional[str],
    subpath: Optional[str],
) -> Optional[PackageURL]:
    """Handler for SSH URLs."""
    match = SSH_REGEX.match(remote_url)
    if match:
        domain = NO_FETCH_EXTRACT(match.group("host")).domain

        parts: list[str] = []
        if domain not in EXCLUDED_DOMAINS:
            parts.append(domain)

        path = match.group("path")
        if path:
            parts.extend(path.replace(".git", "").split("/"))
        name = parts[-1] if parts else DEFAULT_NAME
        namespace = "/".join(parts[:-1])
        return PackageURL(
            type="generic",
            namespace=namespace,
            name=name,
            version=version,
            qualifiers={"vcs_url": remote_url},
            subpath=subpath,
        )
    return None


def _handle_generic(
    remote_url: str,
    path: str,
    version: Optional[str],
    subpath: Optional[str],
) -> PackageURL:
    """Fallback handler for generic URLs."""
    domain = NO_FETCH_EXTRACT(remote_url).domain

    parts: list[str] = []
    if domain not in EXCLUDED_DOMAINS:
        parts.append(domain)

    if path:
        parts.extend(path.replace(".git", "").split("/"))
    name = parts[-1] if parts else DEFAULT_NAME
    namespace = "/".join(parts[:-1])
    return PackageURL(
        type="generic",
        namespace=namespace,
        name=name,
        version=version,
        qualifiers={"vcs_url": remote_url},
        subpath=subpath,
    )


def remote_url_to_purl(
    remote_url: str, version: Optional[str] = None, subpath: Optional[str] = None
) -> PackageURL:
    """Convert a remote URL to a valid PackageURL object.

    Supports GitHub, Bitbucket, SVN, SSH paths.
    Optionally specify version and subpath.
    """
    parsed = urlparse(remote_url)
    path = parsed.path.lstrip("/")

    handlers: List[HandlerType] = [
        _handle_github,
        _handle_bitbucket,
        _handle_svn,
        _handle_ssh,
    ]
    for handler in handlers:
        result: Optional[PackageURL] = handler(remote_url, path, version, subpath)
        if result is not None:
            return result

    return _handle_generic(remote_url, path, version, subpath)
