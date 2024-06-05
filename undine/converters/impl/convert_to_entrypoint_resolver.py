from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine import Entrypoint, InterfaceType, MutationType, QueryType, UnionType
from undine.converters import convert_to_entrypoint_resolver
from undine.exceptions import InvalidEntrypointMutationTypeError
from undine.relay import Connection, Node
from undine.resolvers import (
    BulkCreateResolver,
    BulkDeleteResolver,
    BulkUpdateResolver,
    ConnectionResolver,
    CreateResolver,
    CustomResolver,
    DeleteResolver,
    EntrypointFunctionResolver,
    NodeResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
    UpdateResolver,
)
from undine.resolvers.query import (
    InterfaceResolver,
    UnionTypeResolver,
    _InterfaceConnectionResolver,
    _UnionTypeConnectionResolver,
)
from undine.typing import MutationKind


@convert_to_entrypoint_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]
    return EntrypointFunctionResolver(func=ref, entrypoint=caller)


@convert_to_entrypoint_resolver.register
def _(ref: type[QueryType], **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]
    if caller.many:
        return QueryTypeManyResolver(query_type=ref, entrypoint=caller)
    return QueryTypeSingleResolver(query_type=ref, entrypoint=caller)


@convert_to_entrypoint_resolver.register
def _(ref: type[MutationType], **kwargs: Any) -> GraphQLFieldResolver:
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
                return BulkDeleteResolver(mutation_type=ref)
            return DeleteResolver(mutation_type=ref)

        case MutationKind.custom:
            return CustomResolver(mutation_type=ref)

        case _:
            raise InvalidEntrypointMutationTypeError(ref=ref, kind=ref.__kind__)


@convert_to_entrypoint_resolver.register
def _(ref: type[UnionType], **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]
    return UnionTypeResolver(union_type=ref, entrypoint=caller)


@convert_to_entrypoint_resolver.register
def _(ref: Connection, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Entrypoint = kwargs["caller"]

    if issubclass(ref.query_type, UnionType):
        return _UnionTypeConnectionResolver(connection=ref, entrypoint=caller)

    if isinstance(ref.query_type, InterfaceType):
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
