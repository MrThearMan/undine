from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import (
    GraphQLArgument,
    GraphQLBoolean,
    GraphQLDirective,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLString,
    GraphQLUnionType,
    TypeKind,
    TypeMetaFieldDef,
    introspection_types,
)
from graphql.pyutils import inspect

from .undine_extensions import (
    get_undine_calculation_argument,
    get_undine_connection,
    get_undine_directive,
    get_undine_directive_argument,
    get_undine_entrypoint,
    get_undine_field,
    get_undine_filter,
    get_undine_filterset,
    get_undine_input,
    get_undine_interface_field,
    get_undine_interface_type,
    get_undine_mutation_type,
    get_undine_order,
    get_undine_orderset,
    get_undine_query_type,
    get_undine_union_type,
)
from .utils import get_underlying_type
from .validation_rules.one_of_input_object import is_one_of_input_object

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graphql import DirectiveLocation, GraphQLNamedType, GraphQLOutputType, GraphQLSchema, GraphQLType

    from undine import GQLInfo
    from undine.typing import HasGraphQLExtensions


__all__ = [
    "patch_introspection_schema",
]


__Schema: GraphQLObjectType = introspection_types["__Schema"]  # type: ignore[assignment]
__Directive: GraphQLObjectType = introspection_types["__Directive"]  # type: ignore[assignment]
__DirectiveLocation: GraphQLEnumType = introspection_types["__DirectiveLocation"]  # type: ignore[assignment]
__Type: GraphQLObjectType = introspection_types["__Type"]  # type: ignore[assignment]
__Field: GraphQLObjectType = introspection_types["__Field"]  # type: ignore[assignment]
__InputValue: GraphQLObjectType = introspection_types["__InputValue"]  # type: ignore[assignment]
__EnumValue: GraphQLObjectType = introspection_types["__EnumValue"]  # type: ignore[assignment]
__TypeKind: GraphQLEnumType = introspection_types["__TypeKind"]  # type: ignore[assignment]


def is_visible(obj: HasGraphQLExtensions, info: GQLInfo) -> bool:  # noqa: PLR0911, PLR0912, PLR0914, PLR0915, C901
    match obj:
        case GraphQLObjectType():
            query_type = get_undine_query_type(obj)
            if query_type is not None:
                return query_type.__is_visible__(info.context)

            connection = get_undine_connection(obj)
            if connection is not None:
                return connection.query_type.__is_visible__(info.context)

        case GraphQLInputObjectType():
            mutation_type = get_undine_mutation_type(obj)
            if mutation_type is not None:
                return mutation_type.__is_visible__(info.context)

            filterset = get_undine_filterset(obj)
            if filterset is not None:
                return filterset.__is_visible__(info.context)

        case GraphQLInterfaceType():
            interface_type = get_undine_interface_type(obj)
            if interface_type is not None:
                return interface_type.__is_visible__(info.context)

        case GraphQLUnionType():
            union_type = get_undine_union_type(obj)
            if union_type is not None:
                return union_type.__is_visible__(info.context)

        case GraphQLEnumType():
            orderset = get_undine_orderset(obj)
            if orderset is not None:
                return orderset.__is_visible__(info.context)

        case GraphQLDirective():
            directive = get_undine_directive(obj)
            if directive is not None:
                return directive.__is_visible__(info.context)

        case GraphQLField():
            entrypoint = get_undine_entrypoint(obj)
            if entrypoint is not None:
                if entrypoint.visible_func is not None:
                    return entrypoint.visible_func(entrypoint, info.context)
                return True

            field = get_undine_field(obj)
            if field is not None:
                if field.visible_func is not None:
                    return field.visible_func(entrypoint, info.context)
                return True

            interface_field = get_undine_interface_field(obj)
            if interface_field is not None:
                if interface_field.visible_func is not None:
                    return interface_field.visible_func(interface_field, info.context)
                return True

            field_type = get_underlying_type(obj.type)
            return is_visible(field_type, info)

        case GraphQLInputField():
            inpt = get_undine_input(obj)
            if inpt is not None:
                if inpt.visible_func is not None:
                    return inpt.visible_func(inpt, info.context)
                return True

            ftr = get_undine_filter(obj)
            if ftr is not None:
                if ftr.visible_func is not None:
                    return ftr.visible_func(ftr, info.context)
                return True

            input_field_type = get_underlying_type(obj.type)
            return is_visible(input_field_type, info)

        case GraphQLArgument():
            directive_arg = get_undine_directive_argument(obj)
            if directive_arg is not None:
                if directive_arg.visible_func is not None:
                    return directive_arg.visible_func(directive_arg, info.context)
                return True

            calculation_arg = get_undine_calculation_argument(obj)
            if calculation_arg is not None:
                if calculation_arg.visible_func is not None:
                    return calculation_arg.visible_func(calculation_arg, info.context)
                return True

            arg_type = get_underlying_type(obj.type)
            return is_visible(arg_type, info)

        case GraphQLEnumValue():
            order = get_undine_order(obj)
            if order is not None:
                if order.visible_func is not None:
                    return order.visible_func(order, info.context)
                return True

    return True


def patch_introspection_schema() -> None:
    TypeMetaFieldDef.resolve = resolve_type_meta_field_def

    __Schema._fields = get_schema_fields
    __Directive._fields = get_directive_fields
    __Type._fields = get_type_fields
    __Field._fields = get_field_fields

    # Force re-evaluation of cached properties
    if "fields" in __Schema.__dict__:
        del __Schema.__dict__["fields"]

    if "fields" in __Directive.__dict__:
        del __Directive.__dict__["fields"]

    if "fields" in __Type.__dict__:
        del __Type.__dict__["fields"]

    if "fields" in __Field.__dict__:
        del __Field.__dict__["fields"]


def resolve_type_meta_field_def(root: Any, info: GQLInfo, *, name: str) -> GraphQLNamedType | None:
    gql_type: GraphQLNamedType | None = info.schema.get_type(name)
    if gql_type is None:
        return None

    if not is_visible(gql_type, info):
        return None

    return gql_type


# Schema


def get_schema_fields() -> dict[str, GraphQLField]:
    return {
        "description": GraphQLField(
            GraphQLString,
            resolve=resolve_schema_description,
        ),
        "types": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(__Type))),
            resolve=resolve_schema_types,
            description="A list of all types supported by this server.",
        ),
        "queryType": GraphQLField(
            GraphQLNonNull(__Type),
            resolve=resolve_schema_query_type,
            description="The type that query operations will be rooted at.",
        ),
        "mutationType": GraphQLField(
            __Type,
            resolve=resolve_schema_mutation_type,
            description="If this server supports mutation, the type that mutation operations will be rooted at.",
        ),
        "subscriptionType": GraphQLField(
            __Type,
            resolve=resolve_schema_subscription_type,
            description="If this server support subscription, the type that subscription operations will be rooted at.",
        ),
        "directives": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(__Directive))),
            resolve=resolve_schema_directives,
            description="A list of all directives supported by this server.",
        ),
    }


def resolve_schema_description(root: GraphQLSchema, info: GQLInfo) -> str | None:
    return root.description


def resolve_schema_types(root: GraphQLSchema, info: GQLInfo) -> Iterable[GraphQLNamedType]:
    return [gql_type for gql_type in root.type_map.values() if is_visible(gql_type, info)]


def resolve_schema_query_type(root: GraphQLSchema, info: GQLInfo) -> GraphQLObjectType:
    return root.query_type  # type: ignore[return-value]


def resolve_schema_mutation_type(root: GraphQLSchema, info: GQLInfo) -> GraphQLObjectType | None:
    return root.mutation_type


def resolve_schema_subscription_type(root: GraphQLSchema, info: GQLInfo) -> GraphQLObjectType | None:
    return root.subscription_type


def resolve_schema_directives(root: GraphQLSchema, info: GQLInfo) -> Iterable[GraphQLDirective]:
    return [directive for directive in root.directives if is_visible(directive, info)]


# Directive


def get_directive_fields() -> dict[str, GraphQLField]:
    return {
        "name": GraphQLField(
            GraphQLNonNull(GraphQLString),
            resolve=resolve_directive_name,
        ),
        "description": GraphQLField(
            GraphQLString,
            resolve=resolve_directive_description,
        ),
        "isRepeatable": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            resolve=resolve_directive_is_repeatable,
        ),
        "locations": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(__DirectiveLocation))),
            resolve=resolve_directive_locations,
        ),
        "args": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(__InputValue))),
            args={
                "includeDeprecated": GraphQLArgument(GraphQLBoolean, default_value=False),
            },
            resolve=resolve_directive_args,
        ),
    }


def resolve_directive_name(root: GraphQLDirective, info: GQLInfo) -> str:
    return root.name


def resolve_directive_description(root: GraphQLDirective, info: GQLInfo) -> str | None:
    return root.description


def resolve_directive_is_repeatable(root: GraphQLDirective, info: GQLInfo) -> bool:
    return root.is_repeatable


def resolve_directive_locations(root: GraphQLDirective, info: GQLInfo) -> Iterable[DirectiveLocation]:
    return root.locations


def resolve_directive_args(root: GraphQLDirective, info: GQLInfo, **kwargs: Any) -> list[tuple[str, GraphQLArgument]]:
    args = ((key, arg) for key, arg in root.args.items() if is_visible(arg, info))

    if kwargs["includeDeprecated"]:
        return list(args)

    return [(key, value) for key, value in args if value.deprecation_reason is None]


# Type


def get_type_fields() -> dict[str, GraphQLField]:
    return {
        "kind": GraphQLField(
            GraphQLNonNull(__TypeKind),
            resolve=resolve_type_kind,
        ),
        "name": GraphQLField(
            GraphQLString,
            resolve=resolve_type_name,
        ),
        "description": GraphQLField(
            GraphQLString,
            resolve=resolve_type_description,
        ),
        "specifiedByURL": GraphQLField(
            GraphQLString,
            resolve=resolve_type_specified_by_url,
        ),
        "fields": GraphQLField(
            GraphQLList(GraphQLNonNull(__Field)),
            args={
                "includeDeprecated": GraphQLArgument(GraphQLBoolean, default_value=False),
            },
            resolve=resolve_type_fields,
        ),
        "interfaces": GraphQLField(
            GraphQLList(GraphQLNonNull(__Type)),
            resolve=resolve_type_interfaces,
        ),
        "possibleTypes": GraphQLField(
            GraphQLList(GraphQLNonNull(__Type)),
            resolve=resolve_type_possible_types,
        ),
        "enumValues": GraphQLField(
            GraphQLList(GraphQLNonNull(__EnumValue)),
            args={
                "includeDeprecated": GraphQLArgument(GraphQLBoolean, default_value=False),
            },
            resolve=resolve_type_enum_values,
        ),
        "inputFields": GraphQLField(
            GraphQLList(GraphQLNonNull(__InputValue)),
            args={
                "includeDeprecated": GraphQLArgument(GraphQLBoolean, default_value=False),
            },
            resolve=resolve_type_input_fields,
        ),
        "ofType": GraphQLField(
            __Type,
            resolve=resolve_type_of_type,
        ),
        "isOneOf": GraphQLField(
            GraphQLBoolean,
            resolve=resolve_type_is_one_of,
        ),
    }


def resolve_type_kind(gql_type: GraphQLType, info: GQLInfo) -> TypeKind:
    match gql_type:
        case GraphQLScalarType():
            return TypeKind.SCALAR
        case GraphQLObjectType():
            return TypeKind.OBJECT
        case GraphQLInterfaceType():
            return TypeKind.INTERFACE
        case GraphQLUnionType():
            return TypeKind.UNION
        case GraphQLEnumType():
            return TypeKind.ENUM
        case GraphQLInputObjectType():
            return TypeKind.INPUT_OBJECT
        case GraphQLList():
            return TypeKind.LIST
        case GraphQLNonNull():
            return TypeKind.NON_NULL

    msg = f"Unexpected type: {inspect(gql_type)}."  # pragma: no cover
    raise TypeError(msg)  # pragma: no cover


def resolve_type_name(gql_type: GraphQLType, info: GQLInfo) -> str | None:
    return getattr(gql_type, "name", None)


def resolve_type_description(gql_type: GraphQLType, info: GQLInfo) -> str | None:
    return getattr(gql_type, "description", None)


def resolve_type_specified_by_url(gql_type: GraphQLType, info: GQLInfo) -> str | None:
    return getattr(gql_type, "specified_by_url", None)


def resolve_type_fields(gql_type: GraphQLType, info: GQLInfo, **kwargs: Any) -> list[tuple[str, GraphQLField]] | None:
    if isinstance(gql_type, (GraphQLObjectType, GraphQLInterfaceType)):
        fields = (
            (key, field)
            for key, field in gql_type.fields.items()
            if is_visible(field, info) and is_visible(get_underlying_type(field.type), info)
        )

        if kwargs["includeDeprecated"]:
            return list(fields)

        return [(key, value) for key, value in fields if value.deprecation_reason is None]

    return None


def resolve_type_interfaces(gql_type: GraphQLType, info: GQLInfo) -> Iterable[GraphQLInterfaceType] | None:
    if isinstance(gql_type, (GraphQLObjectType, GraphQLInterfaceType)):
        return [interface for interface in gql_type.interfaces if is_visible(interface, info)]

    return None


def resolve_type_possible_types(gql_type: GraphQLType, info: GQLInfo) -> Iterable[GraphQLObjectType] | None:
    if isinstance(gql_type, (GraphQLInterfaceType, GraphQLUnionType)):
        object_types = info.schema.get_possible_types(gql_type)
        return [object_type for object_type in object_types if is_visible(object_type, info)]

    return None


def resolve_type_enum_values(
    gql_type: GraphQLType,
    info: GQLInfo,
    **kwargs: Any,
) -> list[tuple[str, GraphQLEnumValue]] | None:
    if isinstance(gql_type, GraphQLEnumType):
        values = ((key, field) for key, field in gql_type.values.items() if is_visible(field, info))

        if kwargs["includeDeprecated"]:
            return list(values)

        return [(key, value) for key, value in values if value.deprecation_reason is None]

    return None


def resolve_type_input_fields(
    gql_type: GraphQLType,
    info: GQLInfo,
    **kwargs: Any,
) -> list[tuple[str, GraphQLInputField]] | None:
    if isinstance(gql_type, GraphQLInputObjectType):
        fields = (
            (key, field)
            for key, field in gql_type.fields.items()
            if is_visible(field, info) and is_visible(get_underlying_type(field.type), info)
        )

        if kwargs["includeDeprecated"]:
            return list(fields)

        return [(key, value) for key, value in fields if value.deprecation_reason is None]

    return None


def resolve_type_of_type(gql_type: GraphQLType, info: GQLInfo) -> GraphQLType | None:
    return getattr(gql_type, "of_type", None)


def resolve_type_is_one_of(gql_type: GraphQLType, info: GQLInfo) -> bool | None:
    if isinstance(gql_type, GraphQLInputObjectType):
        return is_one_of_input_object(gql_type)
    return None


# Field


def get_field_fields() -> dict[str, GraphQLField]:
    return {
        "name": GraphQLField(
            GraphQLNonNull(GraphQLString),
            resolve=resolve_field_name,
        ),
        "description": GraphQLField(
            GraphQLString,
            resolve=resolve_field_description,
        ),
        "args": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(__InputValue))),
            args={
                "includeDeprecated": GraphQLArgument(GraphQLBoolean, default_value=False),
            },
            resolve=resolve_field_args,
        ),
        "type": GraphQLField(
            GraphQLNonNull(__Type),
            resolve=resolve_field_type,
        ),
        "isDeprecated": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            resolve=resolve_field_is_deprecated,
        ),
        "deprecationReason": GraphQLField(
            GraphQLString,
            resolve=resolve_field_deprecation_reason,
        ),
    }


def resolve_field_name(item: tuple[str, GraphQLField], info: GQLInfo) -> str:
    return item[0]


def resolve_field_description(item: tuple[str, GraphQLField], info: GQLInfo) -> str | None:
    return item[1].description


def resolve_field_args(
    item: tuple[str, GraphQLField],
    info: GQLInfo,
    **kwargs: Any,
) -> list[tuple[str, GraphQLArgument]]:
    args = ((key, arg) for key, arg in item[1].args.items() if is_visible(arg, info))

    if kwargs["includeDeprecated"]:
        return list(args)

    return [item for item in args if item[1].deprecation_reason is None]


def resolve_field_type(item: tuple[str, GraphQLField], info: GQLInfo) -> GraphQLOutputType:
    return item[1].type


def resolve_field_is_deprecated(item: tuple[str, GraphQLField], info: GQLInfo) -> bool:
    return item[1].deprecation_reason is not None


def resolve_field_deprecation_reason(item: tuple[str, GraphQLField], info: GQLInfo) -> str | None:
    return item[1].deprecation_reason
