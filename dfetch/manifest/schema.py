"""StrictYAML schema for the manifest."""

from strictyaml import Bool, Enum, Float, Int, Map, Optional, Seq, Str

NUMBER = Int() | Float()

REMOTE_SCHEMA = Map(
    {
        "name": Str(),
        "url-base": Str(),
        Optional("default"): Bool(),
    }
)

PROJECT_SCHEMA = Map(
    {
        "name": Str(),
        Optional("dst"): Str(),
        Optional("branch"): Str(),
        Optional("tag"): Str(),
        Optional("revision"): Str(),
        Optional("url"): Str(),
        Optional("repo-path"): Str(),
        Optional("remote"): Str(),
        Optional("patch"): Str(),
        Optional("vcs"): Enum(["git", "svn"]),
        Optional("src"): Str(),
        Optional("ignore"): Seq(Str()),
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
