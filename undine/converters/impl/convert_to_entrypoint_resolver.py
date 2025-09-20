from __future__ import annotations

from collections.abc import AsyncIterable
from inspect import isasyncgenfunction, iscoroutinefunction
from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine import Entrypoint, InterfaceType, MutationType, QueryType, UnionType
from undine.converters import convert_to_entrypoint_resolver
from undine.exceptions import InvalidEntrypointMutationTypeError
from undine.parsers import parse_return_annotation
from undine.relay import Connection, Node
from undine.resolvers import (
    BulkCreateResolver,
    BulkDeleteResolver,
    BulkUpdateResolver,
    ConnectionResolver,
    CreateResolver,
    DeleteResolver,
    EntrypointFunctionResolver,
    InterfaceResolver,
    NodeResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
    SubscriptionValueResolver,
    UnionTypeResolver,
    UpdateResolver,
)
from undine.resolvers.query import UnionTypeConnectionResolver, _InterfaceConnectionResolver
from undine.typing import MutationKind
from undine.utils.reflection import get_origin_or_noop, is_subclass


@convert_to_entrypoint_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]
    if isasyncgenfunction(ref):
        return SubscriptionValueResolver()

    if iscoroutinefunction(ref):
        ann = parse_return_annotation(ref)
        origin = get_origin_or_noop(ann)
        if is_subclass(origin, AsyncIterable):
            return SubscriptionValueResolver()

    return EntrypointFunctionResolver(func=ref, entrypoint=caller)


@convert_to_entrypoint_resolver.register
def _(ref: type[QueryType], **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]
    if caller.many:
        return QueryTypeManyResolver(query_type=ref, entrypoint=caller)
    return QueryTypeSingleResolver(query_type=ref, entrypoint=caller)


@convert_to_entrypoint_resolver.register
def _(ref: type[MutationType], **kwargs: Any) -> GraphQLFieldResolver:  # noqa: PLR0911
    caller: Entrypoint = kwargs["caller"]

    match ref.__kind__:
        case MutationKind.create:
            if caller.many:
                return BulkCreateResolver(mutation_type=ref, entrypoint=caller)
            return CreateResolver(mutation_type=ref, entrypoint=caller)

        case MutationKind.update:
            if caller.many:
                return BulkUpdateResolver(mutation_type=ref, entrypoint=caller)
            return UpdateResolver(mutation_type=ref, entrypoint=caller)

        case MutationKind.delete:
            if caller.many:
                return BulkDeleteResolver(mutation_type=ref, entrypoint=caller)
            return DeleteResolver(mutation_type=ref, entrypoint=caller)

        case MutationKind.custom:
            if "pk" in ref.__input_map__:
                if caller.many:
                    return BulkUpdateResolver(mutation_type=ref, entrypoint=caller)
                return UpdateResolver(mutation_type=ref, entrypoint=caller)

            if caller.many:
                return BulkCreateResolver(mutation_type=ref, entrypoint=caller)
            return CreateResolver(mutation_type=ref, entrypoint=caller)

        case _:
            raise InvalidEntrypointMutationTypeError(ref=ref, kind=ref.__kind__)


@convert_to_entrypoint_resolver.register
def _(ref: type[UnionType], **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]
    return UnionTypeResolver(union_type=ref, entrypoint=caller)


@convert_to_entrypoint_resolver.register
def _(ref: Connection, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]

    if ref.union_type is not None:
        return UnionTypeConnectionResolver(connection=ref, entrypoint=caller)

    if ref.interface_type is not None:
        return _InterfaceConnectionResolver(connection=ref, entrypoint=caller)

    return ConnectionResolver(connection=ref, entrypoint=caller)


@convert_to_entrypoint_resolver.register
def _(_: type[Node], **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]
    return NodeResolver(entrypoint=caller)


@convert_to_entrypoint_resolver.register
def _(ref: type[InterfaceType], **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]
    return InterfaceResolver(interface=ref, entrypoint=caller)
