"""StrictYAML schema for the manifest."""

from strictyaml import Bool, Enum, Float, Int, Map, Optional, Regex, Seq

NUMBER = Int() | Float()

# A safe string: no NUL, no control chars
SAFE_STR = Regex(r"^[^\x00-\x1F\x7F-\x9F]*$")

REMOTE_SCHEMA = Map(
    {
        "name": SAFE_STR,
        "url-base": SAFE_STR,
        Optional("default"): Bool(),
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
        Optional("vcs"): Enum(["git", "svn"]),
        Optional("src"): SAFE_STR,
        Optional("ignore"): Seq(SAFE_STR),
    }
)

MANIFEST_SCHEMA = Map(
    {
        "manifest": Map(
            {
                "version": NUMBER,
                Optional("remotes"): Seq(REMOTE_SCHEMA),
                "projects": Seq(PROJECT_SCHEMA),
            }
        )
    }
)
