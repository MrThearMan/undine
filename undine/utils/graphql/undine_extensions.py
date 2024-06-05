from __future__ import annotations

from typing import TYPE_CHECKING

from undine.settings import undine_settings

if TYPE_CHECKING:
    from graphql import (
        GraphQLArgument,
        GraphQLDirective,
        GraphQLEnumType,
        GraphQLEnumValue,
        GraphQLField,
        GraphQLInputField,
        GraphQLInputObjectType,
        GraphQLInterfaceType,
        GraphQLObjectType,
        GraphQLScalarType,
        GraphQLSchema,
        GraphQLUnionType,
    )

    from undine import (
        CalculationArgument,
        Entrypoint,
        Field,
        Filter,
        FilterSet,
        Input,
        InterfaceField,
        InterfaceType,
        MutationType,
        Order,
        OrderSet,
        QueryType,
        RootType,
        UnionType,
    )
    from undine.directives import Directive, DirectiveArgument
    from undine.relay import Connection
    from undine.scalars import ScalarType


__all__ = [
    "get_undine_calculation_argument",
    "get_undine_connection",
    "get_undine_directive",
    "get_undine_directive_argument",
    "get_undine_entrypoint",
    "get_undine_field",
    "get_undine_filter",
    "get_undine_filterset",
    "get_undine_input",
    "get_undine_interface_field",
    "get_undine_interface_type",
    "get_undine_mutation_type",
    "get_undine_order",
    "get_undine_orderset",
    "get_undine_query_type",
    "get_undine_root_type",
    "get_undine_scalar",
    "get_undine_schema_directives",
    "get_undine_union_type",
]


def get_undine_schema_directives(schema: GraphQLSchema) -> list[Directive] | None:
    return schema.extensions.get(undine_settings.SCHEMA_DIRECTIVES_EXTENSIONS_KEY)


def get_undine_root_type(object_type: GraphQLObjectType) -> type[RootType] | None:
    return object_type.extensions.get(undine_settings.ROOT_TYPE_EXTENSIONS_KEY)


def get_undine_entrypoint(field: GraphQLField) -> Entrypoint | None:
    return field.extensions.get(undine_settings.ENTRYPOINT_EXTENSIONS_KEY)


def get_undine_query_type(object_type: GraphQLObjectType) -> type[QueryType] | None:
    return object_type.extensions.get(undine_settings.QUERY_TYPE_EXTENSIONS_KEY)


def get_undine_field(field: GraphQLField) -> Field | None:
    return field.extensions.get(undine_settings.FIELD_EXTENSIONS_KEY)


def get_undine_interface_type(object_type: GraphQLInterfaceType) -> type[InterfaceType] | None:
    return object_type.extensions.get(undine_settings.INTERFACE_TYPE_EXTENSIONS_KEY)


def get_undine_interface_field(field: GraphQLField) -> InterfaceField | None:
    return field.extensions.get(undine_settings.INTERFACE_FIELD_EXTENSIONS_KEY)


def get_undine_mutation_type(object_type: GraphQLInputObjectType) -> type[MutationType] | None:
    return object_type.extensions.get(undine_settings.MUTATION_TYPE_EXTENSIONS_KEY)


def get_undine_input(field: GraphQLInputField) -> Input | None:
    return field.extensions.get(undine_settings.INPUT_EXTENSIONS_KEY)


def get_undine_filterset(object_type: GraphQLInputObjectType) -> type[FilterSet] | None:
    return object_type.extensions.get(undine_settings.FILTERSET_EXTENSIONS_KEY)


def get_undine_filter(field: GraphQLInputField) -> Filter | None:
    return field.extensions.get(undine_settings.FILTER_EXTENSIONS_KEY)


def get_undine_orderset(enum: GraphQLEnumType) -> type[OrderSet] | None:
    return enum.extensions.get(undine_settings.ORDERSET_EXTENSIONS_KEY)


def get_undine_order(value: GraphQLEnumValue) -> Order | None:
    return value.extensions.get(undine_settings.ORDER_EXTENSIONS_KEY)


def get_undine_connection(object_type: GraphQLObjectType) -> Connection | None:
    return object_type.extensions.get(undine_settings.CONNECTION_EXTENSIONS_KEY)


def get_undine_directive(directive: GraphQLDirective) -> type[Directive] | None:
    return directive.extensions.get(undine_settings.DIRECTIVE_EXTENSIONS_KEY)


def get_undine_directive_argument(argument: GraphQLArgument) -> DirectiveArgument | None:
    return argument.extensions.get(undine_settings.DIRECTIVE_ARGUMENT_EXTENSIONS_KEY)


def get_undine_scalar(scalar: GraphQLScalarType) -> ScalarType | None:
    return scalar.extensions.get(undine_settings.SCALAR_EXTENSIONS_KEY)


def get_undine_union_type(union: GraphQLUnionType) -> type[UnionType] | None:
    return union.extensions.get(undine_settings.UNION_TYPE_EXTENSIONS_KEY)


def get_undine_calculation_argument(arg: GraphQLArgument) -> CalculationArgument | None:
    return arg.extensions.get(undine_settings.CALCULATION_ARGUMENT_EXTENSIONS_KEY)
