from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver, GraphQLType

from undine import InterfaceType, QueryType, UnionType
from undine.converters import convert_to_federation_field_resolver
from undine.dataclasses import TypeRef
from undine.exceptions import MissingFederationFieldResolverError
from undine.federation.directives import ExternalDirective, KeyDirective
from undine.federation.federation_type import (
    FederationField,
    FederationFieldFunctionResolver,
    FederationFieldResolver,
    FederationType,
)


@convert_to_federation_field_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    caller: FederationField = kwargs["caller"]
    return FederationFieldFunctionResolver(func=ref, field=caller)


@convert_to_federation_field_resolver.register
def _(
    ref: type[QueryType | FederationType | InterfaceType | UnionType] | TypeRef | GraphQLType,
    **kwargs: Any,
) -> GraphQLFieldResolver:
    caller: FederationField = kwargs["caller"]

    for directive in caller.federation_type.__directives__:
        if not isinstance(directive, KeyDirective):
            continue
        fields = directive.__parameters__["fields"]
        if caller.schema_name in fields.split():
            return FederationFieldResolver(field=caller)

    if any(isinstance(directive, ExternalDirective) for directive in caller.directives):
        return FederationFieldResolver(field=caller)

    raise MissingFederationFieldResolverError(cls=caller.federation_type, name=caller.name)
