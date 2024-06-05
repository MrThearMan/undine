from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeGuard, TypeVar

from django.db.models import ForeignKey
from graphql import (
    FieldNode,
    GraphQLEnumType,
    GraphQLError,
    GraphQLIncludeDirective,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSkipDirective,
    GraphQLUnionType,
    OperationDefinitionNode,
    OperationType,
    get_argument_values,
    get_directive_values,
)

from undine.exceptions import (
    DirectiveLocationError,
    GraphQLGetRequestMultipleOperationsNoOperationNameError,
    GraphQLGetRequestNonQueryOperationError,
    GraphQLGetRequestNoOperationError,
    GraphQLGetRequestOperationNotFoundError,
)
from undine.utils.text import to_snake_case

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from graphql import (
        DirectiveLocation,
        DocumentNode,
        GraphQLList,
        GraphQLNonNull,
        GraphQLOutputType,
        GraphQLWrappingType,
        SelectionNode,
    )
    from graphql.execution.values import NodeWithDirective

    from undine import Field, GQLInfo
    from undine.directives import Directive
    from undine.typing import ModelField


__all__ = [
    "check_directives",
    "get_arguments",
    "get_queried_field_name",
    "get_underlying_type",
    "is_connection",
    "is_edge",
    "is_node_interface",
    "is_page_info",
    "is_relation_id",
    "should_skip_node",
    "with_graphql_error_path",
]


TGraphQLType = TypeVar(
    "TGraphQLType",
    GraphQLScalarType,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLUnionType,
    GraphQLEnumType,
    GraphQLInputObjectType,
)


# Getters


def get_underlying_type(
    gql_type: (
        TGraphQLType
        | GraphQLList[TGraphQLType]
        | GraphQLList[GraphQLNonNull[TGraphQLType]]
        | GraphQLNonNull[TGraphQLType]
        | GraphQLNonNull[GraphQLList[TGraphQLType]]
        | GraphQLNonNull[GraphQLList[GraphQLNonNull[TGraphQLType]]]
        | GraphQLWrappingType[TGraphQLType]
    ),
) -> TGraphQLType:
    while hasattr(gql_type, "of_type"):
        gql_type = gql_type.of_type
    return gql_type


def get_arguments(info: GQLInfo) -> dict[str, Any]:
    """Get input arguments for the current field from the GraphQL resolve info."""
    graphql_field = info.parent_type.fields[info.field_name]
    return get_argument_values(graphql_field, info.field_nodes[0], info.variable_values)


def get_queried_field_name(original_name: str, info: GQLInfo) -> str:
    """Get the name of a field in the current query."""
    return original_name if info.path.key == info.field_name else info.path.key  # type: ignore[return-value]


# Predicates


def is_connection(field_type: GraphQLOutputType) -> TypeGuard[GraphQLObjectType]:
    return (
        isinstance(field_type, GraphQLObjectType)
        and field_type.name.endswith("Connection")
        and "pageInfo" in field_type.fields
        and "edges" in field_type.fields
    )


def is_edge(field_type: GraphQLOutputType) -> TypeGuard[GraphQLObjectType]:
    return (
        isinstance(field_type, GraphQLObjectType)
        and field_type.name.endswith("Edge")
        and "cursor" in field_type.fields
        and "node" in field_type.fields
    )


def is_node_interface(field_type: GraphQLOutputType) -> TypeGuard[GraphQLInterfaceType]:
    return (
        isinstance(field_type, GraphQLInterfaceType)  # comment here for better formatting
        and field_type.name == "Node"
        and "id" in field_type.fields
    )


def is_page_info(field_type: GraphQLOutputType) -> TypeGuard[GraphQLObjectType]:
    return (
        isinstance(field_type, GraphQLObjectType)
        and field_type.name == "PageInfo"
        and "hasNextPage" in field_type.fields
        and "hasPreviousPage" in field_type.fields
        and "startCursor" in field_type.fields
        and "endCursor" in field_type.fields
    )


def is_typename_metafield(field_node: SelectionNode) -> TypeGuard[FieldNode]:
    if not isinstance(field_node, FieldNode):
        return False
    return field_node.name.value.lower() == "__typename"


def is_relation_id(field: ModelField, field_node: FieldNode) -> TypeGuard[Field]:
    return isinstance(field, ForeignKey) and field.get_attname() == to_snake_case(field_node.name.value)


def should_skip_node(node: NodeWithDirective, variable_values: dict[str, Any]) -> bool:
    skip_args = get_directive_values(GraphQLSkipDirective, node, variable_values)
    if skip_args is not None and skip_args["if"] is True:
        return True

    include_args = get_directive_values(GraphQLIncludeDirective, node, variable_values)
    return include_args is not None and include_args["if"] is False


# Misc.


@contextmanager
def with_graphql_error_path(info: GQLInfo, *, key: str | int | None = None) -> Generator[None, None, None]:
    """Context manager that sets the path of all GraphQL errors raised during its context."""
    try:
        yield
    except GraphQLError as error:
        if error.path is None:
            if key is not None:
                error.path = info.path.add_key(key).as_list()
            else:
                error.path = info.path.as_list()
        raise


def check_directives(directives: Iterable[Directive] | None, *, location: DirectiveLocation) -> None:
    """Check that given directives are allowed in the given location."""
    if directives is None:
        return

    for directive in directives:
        if location not in directive.__locations__:
            raise DirectiveLocationError(directive=directive, location=location)


def validate_get_request_operation(document: DocumentNode, operation_name: str | None = None) -> None:
    """Validates that the operation in the document can be executed in an HTTP GET request."""
    operation_definitions: list[OperationDefinitionNode] = [
        definition_node
        for definition_node in document.definitions
        if isinstance(definition_node, OperationDefinitionNode)
    ]

    if len(operation_definitions) == 0:
        raise GraphQLGetRequestNoOperationError

    if operation_name is None:
        if len(operation_definitions) != 1:
            raise GraphQLGetRequestMultipleOperationsNoOperationNameError

        if operation_definitions[0].operation != OperationType.QUERY:
            raise GraphQLGetRequestNonQueryOperationError

        return

    for operation in operation_definitions:
        if operation.name is None:
            continue

        if operation.name.value != operation_name:
            continue

        if operation.operation != OperationType.QUERY:
            raise GraphQLGetRequestNonQueryOperationError

        return

    raise GraphQLGetRequestOperationNotFoundError(operation_name=operation_name)
