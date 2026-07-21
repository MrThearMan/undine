from __future__ import annotations

from graphql import (
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLString,
)

from undine.settings import undine_settings

__all__ = [
    "FederationAnyScalar",
    "FederationContextFieldValue",
    "FederationFieldSet",
    "FederationLinkImport",
    "FederationLinkPurpose",
    "FederationPolicy",
    "FederationScope",
    "FederationServiceType",
]


FederationAnyScalar = GraphQLScalarType(
    name="_Any",
    extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
)


FederationFieldSet = GraphQLScalarType(
    name="FieldSet",
    extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
)


FederationLinkImport = GraphQLScalarType(
    name="link__Import",
    extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
)


FederationLinkPurpose = GraphQLEnumType(
    name="link__Purpose",
    values={
        "SECURITY": GraphQLEnumValue(value="SECURITY"),
        "EXECUTION": GraphQLEnumValue(value="EXECUTION"),
    },
    extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
)


FederationContextFieldValue = GraphQLScalarType(
    name="ContextFieldValue",
    extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
)


FederationScope = GraphQLScalarType(
    name="federation__Scope",
    extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
)


FederationPolicy = GraphQLScalarType(
    name="federation__Policy",
    extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
)


FederationServiceType = GraphQLObjectType(
    name="_Service",
    fields={"sdl": GraphQLField(GraphQLNonNull(GraphQLString))},
    extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
)
