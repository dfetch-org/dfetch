"""Validate manifests."""

from typing import Any

import yamale
from yamale.validators.constraints import Constraint
from yamale.validators.validators import DefaultValidators, List

import dfetch.resources


class UniqueItemsByProperty(Constraint):  # type: ignore
    """Ensure a certain property is unique."""

    keywords = {"unique_property": str}

    def __init__(self, value_type: Any, kwargs: Any):
        """Create Unique Items by Property constraint.

        inspired by https://github.com/23andMe/Yamale/issues/201
        """
        super().__init__(value_type, kwargs)
        self.fail = ""

    def _is_valid(self, value: Any) -> bool:

        unique_property = getattr(self, "unique_property", None)

        if not value or not unique_property:
            return True

        seen: dict[str, set[Any]] = {
            property_name.strip(): set() for property_name in unique_property.split(",")
        }

        for item in value:
            for prop_name, prev_values in seen.items():

                if prop_name in item.keys():
                    property_ = item[prop_name]

                    if property_ in prev_values:
                        self.fail = (
                            f"Property '{prop_name}' is not unique."
                            f" Duplicate value '{property_}'"
                        )
                        return False

                    prev_values.add(property_)
        return True

    def _fail(self, value: Any) -> str:
        return self.fail


def validate(path: str) -> None:
    """Validate the given manifest."""
    with dfetch.resources.schema_path() as schema_path:

        validators = DefaultValidators.copy()
        validators[List.tag].constraints.append(UniqueItemsByProperty)

        validation_result = yamale.validate(
            schema=yamale.make_schema(str(schema_path), validators=validators),
            data=yamale.make_data(path),
            _raise_error=False,
        )

        for result in validation_result:
            if result.errors:
                raise RuntimeError(
                    "Schema validation failed:\n- " + "\n- ".join(result.errors)
                )
