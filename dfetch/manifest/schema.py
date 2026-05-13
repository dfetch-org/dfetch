"""StrictYAML schema for the manifest."""

from strictyaml import Bool, Enum, Float, Int, Map, Optional, Regex, Seq, Str

# A safe string: no NUL, no control chars
SAFE_STR = Regex(r"^[^\x00-\x1F\x7F-\x9F]*$")

# Version accepts an unquoted integer (version: 0), an unquoted float
# (version: 0.0), or a quoted string (version: '0.0').  Manifest code
# always converts the result to str before using or writing it.
VERSION = Int() | Float() | Str()

REMOTE_SCHEMA = Map(
    {
        "name": SAFE_STR,
        "url-base": SAFE_STR,
        Optional("default"): Bool(),
    }
)

HASH_STR = Regex(
    r"^(sha256:[a-fA-F0-9]{64}|sha384:[a-fA-F0-9]{96}|sha512:[a-fA-F0-9]{128})$"
)

# ``integrity:`` block — designed for future extension with ``sig:`` and
# ``sig-key:`` fields for detached signature / signing-key verification.
INTEGRITY_MAP = Map(
    {
        Optional("hash"): HASH_STR,
        # Future fields (uncomment when implemented):
        # Optional("sig"): SAFE_STR,      # detached signature URL (.sig / .asc)
        # Optional("sig-key"): SAFE_STR,  # signing-key URL or fingerprint (.p7s / .gpg)
    }
)

PROJECT_SCHEMA = Map(
    {
        "name": SAFE_STR,
        Optional("dst"): SAFE_STR,
        Optional("branch"): SAFE_STR,
        Optional("tag"): SAFE_STR,
        Optional("revision"): SAFE_STR,
        Optional("url"): SAFE_STR,
        Optional("repo-path"): SAFE_STR,
        Optional("remote"): SAFE_STR,
        Optional("patch"): SAFE_STR | Seq(SAFE_STR),
        Optional("vcs"): Enum(["git", "svn", "archive"]),
        Optional("src"): SAFE_STR,
        Optional("ignore"): Seq(SAFE_STR),
        Optional("integrity"): INTEGRITY_MAP,
    }
)

MANIFEST_SCHEMA = Map(
    {
        "manifest": Map(
            {
                "version": VERSION,
                Optional("remotes"): Seq(REMOTE_SCHEMA),
                Optional("projects"): Seq(PROJECT_SCHEMA),
            }
        )
    }
)
