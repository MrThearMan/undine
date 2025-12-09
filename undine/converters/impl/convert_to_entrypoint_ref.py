from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import UndefinedType

from undine import Entrypoint, InterfaceType, MutationType, QueryType, UnionType
from undine.converters import convert_to_entrypoint_ref, is_many
from undine.exceptions import MissingEntrypointRefError
from undine.pagination import OffsetPagination
from undine.parsers import parse_is_nullable
from undine.relay import Connection, Node
from undine.settings import undine_settings
from undine.subscriptions import SignalSubscription


@convert_to_entrypoint_ref.register
def _(_: UndefinedType, **kwargs: Any) -> Any:
    caller: Entrypoint = kwargs["caller"]
    raise MissingEntrypointRefError(name=caller.name, cls=caller.root_type)


@convert_to_entrypoint_ref.register
def _(ref: FunctionType, **kwargs: Any) -> Any:
    caller: Entrypoint = kwargs["caller"]
    caller.many = is_many(ref)
    caller.nullable = parse_is_nullable(ref)
    return ref


@convert_to_entrypoint_ref.register
def _(ref: type[QueryType], **kwargs: Any) -> Any:
    return ref


@convert_to_entrypoint_ref.register
def _(ref: type[MutationType], **kwargs: Any) -> Any:
    return ref


@convert_to_entrypoint_ref.register
def _(ref: type[UnionType], **kwargs: Any) -> Any:
    caller: Entrypoint = kwargs["caller"]
    caller.many = True
    return ref


@convert_to_entrypoint_ref.register
def _(ref: type[InterfaceType], **kwargs: Any) -> Any:
    caller: Entrypoint = kwargs["caller"]
    caller.many = True
    return ref


@convert_to_entrypoint_ref.register
def _(ref: type[Node], **kwargs: Any) -> Any:
    caller: Entrypoint = kwargs["caller"]
    caller.many = False
    return ref


@convert_to_entrypoint_ref.register
def _(ref: Connection, **kwargs: Any) -> Any:
    caller: Entrypoint = kwargs["caller"]
    caller.many = False
    caller.extensions[undine_settings.CONNECTION_EXTENSIONS_KEY] = ref
    return ref


@convert_to_entrypoint_ref.register
def _(ref: OffsetPagination, **kwargs: Any) -> Any:
    caller: Entrypoint = kwargs["caller"]
    caller.many = True
    caller.extensions[undine_settings.OFFSET_PAGINATION_EXTENSIONS_KEY] = ref
    return ref


@convert_to_entrypoint_ref.register
def _(ref: SignalSubscription, **kwargs: Any) -> Any:
    caller: Entrypoint = kwargs["caller"]
    caller.many = False
    return ref
