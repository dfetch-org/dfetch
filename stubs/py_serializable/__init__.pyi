"""Partial type stub for py_serializable.

The published package types @serializable_class as returning
  Union[Type[T], _JsonSerializable, _XmlSerializable]
(it aliases Union as "Intersection").  That union causes pyright to lose the
concrete constructor signature on every decorated class.  This stub overrides
the decorator so it correctly preserves Type[T], which is what actually happens
at runtime.
"""

from collections.abc import Callable, Iterable
from typing import Any, TypeVar, overload

from typing_extensions import Self

_T = TypeVar("_T")

class _Serializable:
    def as_json(self) -> str: ...
    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self | None: ...
    def as_xml(self) -> Any: ...
    @classmethod
    def from_xml(cls, data: Any) -> Self | None: ...

@overload
def serializable_class(
    cls: None = ...,
    *,
    name: str | None = ...,
    serialization_types: Iterable[Any] | None = ...,
    ignore_during_deserialization: Iterable[str] | None = ...,
    ignore_unknown_during_deserialization: bool = ...,
) -> Callable[[type[_T]], type[_T]]: ...
@overload
def serializable_class(
    cls: type[_T],
    *,
    name: str | None = ...,
    serialization_types: Iterable[Any] | None = ...,
    ignore_during_deserialization: Iterable[str] | None = ...,
    ignore_unknown_during_deserialization: bool = ...,
) -> type[_T]: ...
def serializable_class(cls: Any = None, **kwargs: Any) -> Any: ...
def xml_name(name: str) -> Callable[[_T], _T]: ...
def xml_sequence(order: int) -> Callable[[_T], _T]: ...
def xml_array(
    array_type: Any,
    child_name: str | None = ...,
) -> Callable[[_T], _T]: ...
def xml_attribute() -> Callable[[_T], _T]: ...
def xml_string(string_type: Any) -> Callable[[_T], _T]: ...
def type_mapping(type_: type) -> Callable[[_T], _T]: ...
def allow_none() -> Callable[[_T], _T]: ...
def as_int() -> Callable[[_T], _T]: ...
def serializable_enum(cls: type[_T]) -> type[_T]: ...
def view(view_: Any) -> Callable[[_T], _T]: ...

class XmlStringSerializationType:
    NORMALIZED_STRING: str
    TOKEN: str

class ViewType: ...
