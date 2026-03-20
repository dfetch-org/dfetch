"""Module to convert remote URLs to valid Package URLs (PURLs).

Supports: GitHub, Bitbucket, SVN, SSH paths, archives, and more.
"""

import os.path
import re
from urllib.parse import urlparse

from packageurl import PackageURL
from tldextract import TLDExtract

from dfetch.vcs.archive import ARCHIVE_EXTENSIONS

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

# Map from dfetch hash-field algorithm prefix to CycloneDX HashAlgorithm name
DFETCH_TO_CDX_HASH_ALGORITHM: dict[str, str] = {
    "sha256": "SHA-256",
    "sha384": "SHA-384",
    "sha512": "SHA-512",
}

# Name given to a package or group if it is not extractable from the URL
DEFAULT_NAME = "unknown"


def _is_archive_url(url: str) -> bool:
    """Return *True* when *url* points to a recognised archive file."""
    lower = url.lower().split("?")[0]  # strip query string before checking extension
    return any(lower.endswith(ext) for ext in ARCHIVE_EXTENSIONS)


def _strip_archive_extension(name: str) -> str:
    """Remove a recognised archive extension from *name*."""
    lower = name.lower()
    # Check multi-part extensions first (.tar.gz etc.)
    for ext in ARCHIVE_EXTENSIONS:
        if lower.endswith(ext):
            return name[: -len(ext)]
    return name


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
    remote_url: str, version: str | None = None, subpath: str | None = None
) -> PackageURL | None:
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


def _archive_purl(
    remote_url: str, version: str | None, subpath: str | None
) -> PackageURL:
    """Build a generic PURL for an archive URL."""
    parsed = urlparse(remote_url)
    basename = os.path.basename(parsed.path)
    name = _strip_archive_extension(basename) or DEFAULT_NAME
    namespace = parsed.hostname or ""
    return PackageURL(
        type="generic",
        namespace=namespace or None,
        name=name,
        version=version,
        qualifiers={"download_url": remote_url},
        subpath=subpath,
    )


def _vcs_namespace_and_name(remote_url: str) -> tuple[str, str, str]:
    """Derive namespace, name, and normalised URL for a generic VCS remote URL.

    Returns:
        A ``(namespace, name, remote_url)`` tuple where *remote_url* may have
        been normalised (e.g. SSH short-form converted to ``ssh://`` scheme).
    """
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
                match.group("host"), match.group("path")
            )
            if not parsed.scheme:
                remote_url = f"ssh://{parsed.path.replace(':', '/')}"
        else:
            namespace, name = _namespace_and_name_from_domain_and_path(
                remote_url, path.replace(".git", "")
            )
    return namespace, name, remote_url


def remote_url_to_purl(
    remote_url: str, version: str | None = None, subpath: str | None = None
) -> PackageURL:
    """Convert a remote URL to a valid PackageURL object.

    Supports GitHub, Bitbucket, SVN, SSH paths, and archive downloads.
    Optionally specify version and subpath.
    """
    purl = _known_purl_types(remote_url, version, subpath)
    if purl:
        return purl
    if _is_archive_url(remote_url):
        return _archive_purl(remote_url, version, subpath)
    namespace, name, remote_url = _vcs_namespace_and_name(remote_url)
    return PackageURL(
        type="generic",
        namespace=namespace,
        name=name,
        version=version,
        qualifiers={"vcs_url": remote_url},
        subpath=subpath,
    )
