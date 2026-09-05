from __future__ import annotations

from typing import Any

from undine import InterfaceType, MutationType, QueryType, UnionType
from undine.converters import convert_to_entrypoint_complexity
from undine.pagination import OffsetPagination
from undine.relay import Connection, Node

MEMBER_COMPLEXITY_INFO = (
    "The maximum. Undine counts one for the entrypoint, plus one for each member the operation selects fields from."
)


@convert_to_entrypoint_complexity.register
def _(_: Any, **kwargs: Any) -> int:
    return 0


@convert_to_entrypoint_complexity.register
def _(_: type[QueryType], **kwargs: Any) -> int:
    return 1


@convert_to_entrypoint_complexity.register
def _(_: type[MutationType], **kwargs: Any) -> int:
    return 1


@convert_to_entrypoint_complexity.register
def _(_: type[Node], **kwargs: Any) -> int:
    return 1


@convert_to_entrypoint_complexity.register
def _(_: type[UnionType], **kwargs: Any) -> int:
    return 1


@convert_to_entrypoint_complexity.register
def _(_: type[InterfaceType], **kwargs: Any) -> int:
    return 1


@convert_to_entrypoint_complexity.register
def _(ref: Connection, **kwargs: Any) -> int:
    inner_ref = ref.query_type or ref.union_type or ref.interface_type
    return convert_to_entrypoint_complexity(inner_ref, **kwargs)


@convert_to_entrypoint_complexity.register
def _(ref: OffsetPagination, **kwargs: Any) -> int:
    inner_ref = ref.query_type or ref.union_type or ref.interface_type
    return convert_to_entrypoint_complexity(inner_ref, **kwargs)
