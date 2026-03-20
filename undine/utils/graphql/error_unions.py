from __future__ import annotations

from inspect import cleandoc
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from graphql import GraphQLError, GraphQLField, GraphQLNonNull, GraphQLString, GraphQLUnionType

from undine.typing import ErrorUnionFieldErrorDict, ErrorUnionFieldValueDict
from undine.utils.graphql.type_registry import get_or_create_graphql_interface_type, get_or_create_graphql_object_type

if TYPE_CHECKING:
    from graphql import GraphQLAbstractType, GraphQLFieldResolver, GraphQLObjectType, GraphQLOutputType

    from undine import GQLInfo
    from undine.typing import ErrorUnionType


__all__ = [
    "build_union_with_errors",
    "default_union_error_resolver",
    "error_union_resolver_wrapper",
    "resolve_field_error_message",
]

GraphQLFieldError = get_or_create_graphql_interface_type(
    name="FieldError",
    description="An error that occurred while resolving a field.",
    fields={"message": GraphQLField(GraphQLNonNull(GraphQLString))},
)


def build_union_with_errors(
    name: str,
    field_type: GraphQLOutputType,
    errors: list[type[Exception]],
) -> GraphQLNonNull[GraphQLUnionType]:
    field_type = get_or_create_graphql_object_type(
        name=f"{name}Value",
        fields={"value": GraphQLField(field_type)},
    )

    error_types: dict[type[Exception], GraphQLObjectType] = {
        error: get_or_create_graphql_object_type(
            name=error.__name__,
            description=cleandoc(error.__doc__ or "") or None,
            interfaces=(GraphQLFieldError,),
            fields=getattr(error, "graphql_fields", GraphQLFieldError.fields),
        )
        for error in errors
    }

    def resolve_type(value: ErrorUnionType, info: GQLInfo, abstract_type: GraphQLAbstractType) -> str | None:
        if not isinstance(value, ErrorUnionFieldErrorDict):
            return field_type.name

        for error in errors:
            if isinstance(value.error, error):
                return error_types[error].name

        return None

    return GraphQLNonNull(
        GraphQLUnionType(
            name=name,
            types=(field_type, *error_types.values()),
            resolve_type=resolve_type,  # type: ignore[arg-type]
        )
    )


def error_union_resolver_wrapper(resolver: GraphQLFieldResolver, errors: list[type[Exception]]) -> GraphQLFieldResolver:
    def wrapped_resolver(root: Any, info: GQLInfo, **args: Any) -> ErrorUnionType:
        try:
            result = resolver(root, info, **args)

        except Exception as error:
            for error_type in errors:
                if isinstance(error, error_type):
                    error_resolver: GraphQLFieldResolver
                    error_resolver = getattr(error, "graphql_resolve", default_union_error_resolver)
                    result = error_resolver(error, info, **args)
                    return ErrorUnionFieldErrorDict(result, error=error)
            raise

        return ErrorUnionFieldValueDict(value=result)

    return wrapped_resolver


def default_union_error_resolver(error: Exception, info: GQLInfo, **kwargs: Any) -> dict[str, Any]:
    return {"message": resolve_field_error_message(error)}


def resolve_field_error_message(error: Exception) -> str:
    match error:
        case GraphQLError():
            return error.message
        case ValidationError():
            return error.message % (error.params or {})
        case _:
            return str(getattr(error, "message", error))
