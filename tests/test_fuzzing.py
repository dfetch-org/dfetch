"""Fuzz test the manifest."""

from __future__ import annotations

import os
import re
import tempfile
from contextlib import suppress
from typing import Any, Dict, Mapping, Tuple

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

# StrictYAML is a runtime dependency:
# pip install strictyaml hypothesis
from strictyaml import Any as SyAny
from strictyaml import (
    Bool,
    EmptyList,
    EmptyNone,
    Enum,
    Float,
    Int,
    Map,
    MapPattern,
    Regex,
    Seq,
    Str,
    as_document,
    load,
)

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


def _classname(obj: Any) -> str:
    return obj.__class__.__name__


def _get_map_items(m: Map) -> Mapping[Any, Any]:
    """
    StrictYAML's Map stores the key->validator mapping internally.
    It has varied attribute names across versions; try common ones.
    """
    for attr in ("_validator", "_map", "map", "mapping"):
        val = getattr(m, attr, None)
        if isinstance(val, Mapping):
            return val
    raise TypeError("Unsupported StrictYAML Map internals; cannot find mapping dict.")


def _unwrap_optional_key(k: Any) -> Tuple[str, bool]:
    """
    Returns (key_name, is_optional).
    Optional('b', default=...) is used *as a key* inside Map({...}).
    """
    if _classname(k) == "Optional":
        for attr in ("_key", "key"):
            name = getattr(k, attr, None)
            if isinstance(name, str):
                return name, True
        return str(k), True
    if isinstance(k, str):
        return k, False
    return str(k), False


def _enum_values(e: Enum) -> Any:
    vals = getattr(e, "_restricted_to", None)
    if vals:
        return list(vals)
    raise TypeError("Unsupported StrictYAML Enum internals; cannot read choices.")


def _regex_pattern(r: Regex) -> re.Pattern:
    for attr in ("_regex", "regex", "pattern"):
        pat = getattr(r, attr, None)
        if isinstance(pat, (str, re.Pattern)):
            return re.compile(pat) if isinstance(pat, str) else pat
    raise TypeError("Unsupported StrictYAML Regex internals; cannot read pattern.")


def _mappattern_parts(mp: MapPattern) -> Tuple[Any, Any, int | None, int | None]:
    key_v = None
    val_v = None
    min_k = getattr(mp, "minimum_keys", None)
    max_k = getattr(mp, "maximum_keys", None)
    for attr in ("_key_validator", "key_validator"):
        key_v = getattr(mp, attr, None) or key_v
    for attr in ("_value_validator", "value_validator"):
        val_v = getattr(mp, attr, None) or val_v
    if key_v is None or val_v is None:
        raise TypeError("Unsupported StrictYAML MapPattern internals.")
    return key_v, val_v, min_k, max_k


def strictyaml_to_strategy(
    validator: Any, *, default_text_alphabet=st.characters(), default_max_list=5
):
    """
    Convert a StrictYAML validator into a Hypothesis strategy that yields
    *Python data structures* which conform to the schema.
    """
    name = _classname(validator)

    if isinstance(validator, Str):
        return st.text(alphabet=default_text_alphabet)

    if isinstance(validator, Int):
        return st.integers()

    if isinstance(validator, Float):
        return st.floats(allow_nan=False, allow_infinity=False)

    if isinstance(validator, Bool):
        return st.booleans()

    if isinstance(validator, Enum):
        values = _enum_values(validator)
        return st.sampled_from(values)

    if isinstance(validator, Regex):
        pattern = _regex_pattern(validator)
        return st.from_regex(pattern, fullmatch=True)

    if isinstance(validator, Seq):
        item_v = None
        for attr in ("_validator", "validator", "_item_validator", "item_validator"):
            item_v = getattr(validator, attr, None) or item_v
        if item_v is None:
            raise TypeError(
                "Unsupported StrictYAML Seq internals; cannot find item validator."
            )
        return st.lists(
            strictyaml_to_strategy(
                item_v,
                default_text_alphabet=default_text_alphabet,
                default_max_list=default_max_list,
            ),
            min_size=1,
            max_size=default_max_list,
        )

    if isinstance(validator, EmptyList):
        return st.just([])

    if isinstance(validator, Map):
        items = _get_map_items(validator)
        required: Dict[str, Any] = {}
        optional: Dict[str, Any] = {}

        for raw_key, val_validator in items.items():
            key_name, is_opt = _unwrap_optional_key(raw_key)
            if is_opt:
                optional[key_name] = strictyaml_to_strategy(
                    val_validator,
                    default_text_alphabet=default_text_alphabet,
                    default_max_list=default_max_list,
                )
            else:
                required[key_name] = strictyaml_to_strategy(
                    val_validator,
                    default_text_alphabet=default_text_alphabet,
                    default_max_list=default_max_list,
                )

        base = st.fixed_dictionaries(required)

        def with_optional(base_dict: Dict[str, Any]):
            if not optional:
                return st.just(base_dict)
            opt_kv_strats = [st.tuples(st.just(k), s) for k, s in optional.items()]

            chosen = st.lists(st.one_of(*opt_kv_strats), unique_by=lambda kv: kv[0])
            return chosen.map(lambda kvs: {**base_dict, **dict(kvs)})

        return base.flatmap(with_optional)

    if isinstance(validator, MapPattern):
        key_v, val_v, min_k, max_k = _mappattern_parts(validator)
        key_strat = strictyaml_to_strategy(
            key_v,
            default_text_alphabet=default_text_alphabet,
            default_max_list=default_max_list,
        )
        val_strat = strictyaml_to_strategy(
            val_v,
            default_text_alphabet=default_text_alphabet,
            default_max_list=default_max_list,
        )

        return st.dictionaries(
            keys=key_strat,
            values=val_strat,
            min_size=min_k or 0,
            max_size=max_k or default_max_list,
        )

    if _classname(validator) in ("OrValidator", "Or"):
        children = None

        for attr in ("validators", "_validators", "choices", "_choices"):
            vs = getattr(validator, attr, None)
            if isinstance(vs, (list, tuple)) and len(vs) > 0:
                children = list(vs)
                break

        if children is None:
            left = None
            right = None
            for la in ("_a", "a", "_left", "left", "_lhs", "lhs", "_validator_a"):
                if getattr(validator, la, None) is not None:
                    left = getattr(validator, la)
                    break
            for ra in ("_b", "b", "_right", "right", "_rhs", "rhs", "_validator_b"):
                if getattr(validator, ra, None) is not None:
                    right = getattr(validator, ra)
                    break
            if left is not None and right is not None:
                children = [left, right]

        if not children:
            raise TypeError(
                "Unsupported StrictYAML OrValidator internals; no children found."
            )

        branch_strats = [
            strictyaml_to_strategy(
                c,
                default_text_alphabet=default_text_alphabet,
                default_max_list=default_max_list,
            )
            for c in children
        ]
        return st.one_of(branch_strats)

    if isinstance(validator, SyAny):
        leaf = st.one_of(
            st.booleans(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(),
        )
        return st.recursive(
            leaf,
            lambda inner: st.one_of(
                st.lists(inner, max_size=3),
                st.dictionaries(st.text(), inner, max_size=3),
            ),
            max_leaves=10,
        )

    if isinstance(validator, EmptyNone):
        return st.none()

    # If we reach here, add more mappings (e.g., Decimal, Datetime, Email, etc.) as needed.
    raise NotImplementedError(
        f"No strategy mapping implemented for StrictYAML validator: {name}"
    )


def validate_with_strictyaml(data: Any, yaml_schema: Any) -> None:
    """
    Ensure that 'data' is serializable with the given StrictYAML schema.
    If it doesn't conform, as_document will raise.
    """
    as_document(data, yaml_schema)  # will raise YAMLSerializationError on mismatch


data_strategy = strictyaml_to_strategy(schema)


@given(data_strategy)
def test_data_conforms_to_schema(data):
    """Validate by attempting to serialize via StrictYAML."""
    # If data violates the schema, this raises and Hypothesis will shrink to a minimal counterexample.
    validate_with_strictyaml(data, schema)


@given(data_strategy)
def test_manifest_can_be_created(data):
    """Validate by attempting to construct a Manifest."""
    try:
        Manifest(data)
    except KeyError:
        pass


@given(data_strategy)
def test_check(data):
    """Validate check comand."""
    with suppress(DfetchFatalException):
        with tempfile.TemporaryDirectory() as tmpdir:
            with in_directory(tmpdir):
                with open("dfetch.yaml", "w", encoding="UTF-8") as manifest_file:
                    yaml.dump(data, manifest_file)
                run(["check"])


@given(data_strategy)
def test_update(data):
    """Validate update comand."""
    with suppress(DfetchFatalException):
        with tempfile.TemporaryDirectory() as tmpdir:
            with in_directory(tmpdir):
                with open("dfetch.yaml", "w", encoding="UTF-8") as manifest_file:
                    yaml.dump(data, manifest_file)
                run(["update"])


if __name__ == "__main__":

    settings.load_profile("manual")

    example = data_strategy.example()
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
