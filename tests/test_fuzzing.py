"""Fuzz test the manifest."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from typing import Any

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from strictyaml import as_document, load

from dfetch.__main__ import DfetchFatalException, run
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.schema import MANIFEST_SCHEMA as schema
from dfetch.util.util import in_directory

settings.register_profile(
    "ci",
    max_examples=30,
    deadline=None,
    print_blob=True,
)
settings.register_profile(
    "dev",
    max_examples=100,
    deadline=None,
)
settings.register_profile(
    "manual",
    max_examples=300,
    deadline=None,
)
if os.getenv("CI"):
    settings.load_profile("ci")
else:
    settings.load_profile("dev")

# Avoid control chars and NUL to prevent OS/path/subprocess issues in tests
SAFE_TEXT = st.text(
    alphabet=st.characters(
        min_codepoint=32, blacklist_categories=("Cs",)
    ),  # no controls/surrogates
    min_size=0,
    max_size=64,
)

# NUMBER = Int() | Float()  with finite floats
SAFE_NUMBER = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
)


def opt_str():
    """Small helper for optional text fields."""
    return st.none() | SAFE_TEXT


remote_entry = st.builds(
    lambda name, url_base, default: {
        k: v
        for k, v in {
            "name": name,
            "url-base": url_base,
            "default": default,
        }.items()
        if v is not None
    },
    name=SAFE_TEXT.filter(lambda s: len(s) > 0),
    url_base=SAFE_TEXT.filter(lambda s: len(s) > 0),
    default=st.none() | st.booleans(),
)

vcs_enum = st.sampled_from(["git", "svn"])

ignore_list = st.lists(SAFE_TEXT, min_size=1, max_size=5)

project_entry = st.builds(
    lambda name, dst, branch, tag, revision, url, repo_path, remote, patch, vcs, src, ignore: {
        k: v
        for k, v in {
            "name": name,
            "dst": dst,
            "branch": branch,
            "tag": tag,
            "revision": revision,
            "url": url,
            "repo-path": repo_path,
            "remote": remote,
            "patch": patch,
            "vcs": vcs,
            "src": src,
            "ignore": ignore,
        }.items()
        if v is not None
    },
    name=SAFE_TEXT.filter(lambda s: len(s) > 0),
    dst=opt_str(),
    branch=opt_str(),
    tag=opt_str(),
    revision=opt_str(),
    url=opt_str(),
    repo_path=opt_str(),
    remote=opt_str(),
    patch=opt_str(),
    vcs=st.none() | vcs_enum,
    src=opt_str(),
    ignore=st.one_of(ignore_list, st.just([])),
)

remotes_seq = st.none() | st.lists(remote_entry, min_size=1, max_size=4)
projects_seq = st.lists(project_entry, min_size=1, max_size=6)

manifest_strategy = st.builds(
    lambda version, remotes, projects: {
        "manifest": {
            "version": version,
            **({"remotes": remotes} if remotes is not None else {}),
            "projects": projects,
        }
    },
    version=SAFE_NUMBER,
    remotes=remotes_seq,
    projects=projects_seq,
)


def validate_with_strictyaml(data: Any, yaml_schema: Any) -> None:
    """
    Ensure that 'data' is serializable with the given StrictYAML schema.
    If it doesn't conform, as_document will raise.
    """
    as_document(data, yaml_schema)  # will raise YAMLSerializationError on mismatch


@given(manifest_strategy)
def test_data_conforms_to_schema(data):
    """Validate by attempting to serialize via StrictYAML."""
    # If data violates the schema, this raises and Hypothesis will shrink to a minimal counterexample.
    validate_with_strictyaml(data, schema)


@given(manifest_strategy)
def test_manifest_can_be_created(data):
    """Validate by attempting to construct a Manifest."""
    try:
        Manifest(data)
    except KeyError:
        pass


@given(manifest_strategy)
def test_check(data):
    """Validate check command."""
    with suppress(DfetchFatalException):
        with tempfile.TemporaryDirectory() as tmpdir:
            with in_directory(tmpdir):
                with open("dfetch.yaml", "w", encoding="UTF-8") as manifest_file:
                    yaml.dump(data, manifest_file)
                run(["check"])


@given(manifest_strategy)
def test_update(data):
    """Validate update command."""
    with suppress(DfetchFatalException):
        with tempfile.TemporaryDirectory() as tmpdir:
            with in_directory(tmpdir):
                with open("dfetch.yaml", "w", encoding="UTF-8") as manifest_file:
                    yaml.dump(data, manifest_file)
                run(["update"])


if __name__ == "__main__":

    settings.load_profile("manual")

    example = manifest_strategy.example()
    print("One generated example:\n", example)

    # Show the YAML StrictYAML would emit for the example:
    print("\nYAML output:\n", as_document(example, schema).as_yaml())

    # And ensure parse+validate round-trip works:
    parsed = load(as_document(example, schema).as_yaml(), schema)
    print("\nRound-trip parsed .data:\n", parsed.data)

    test_data_conforms_to_schema()
    test_manifest_can_be_created()
    test_check()
    test_update()
