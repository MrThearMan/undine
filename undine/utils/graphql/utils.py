from __future__ import annotations

from collections.abc import Hashable
from contextlib import contextmanager
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeGuard, TypeVar

from django.db.models import ForeignKey
from graphql import (
    DocumentNode,
    ExecutionResult,
    FieldNode,
    GraphQLEnumType,
    GraphQLError,
    GraphQLIncludeDirective,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLResolveInfo,
    GraphQLScalarType,
    GraphQLSkipDirective,
    GraphQLUnionType,
    OperationDefinitionNode,
    OperationType,
    Undefined,
    get_argument_values,
    get_directive_values,
)

from undine.exceptions import (
    DirectiveLocationError,
    GraphQLErrorGroup,
    GraphQLGetRequestNonQueryOperationError,
    GraphQLRequestMultipleOperationsNoOperationNameError,
    GraphQLRequestNoOperationError,
    GraphQLRequestOperationNotFoundError,
)
from undine.settings import undine_settings
from undine.utils.logging import log_traceback
from undine.utils.model_utils import get_validation_error_messages
from undine.utils.reflection import get_traceback
from undine.utils.text import to_snake_case

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Iterable

    from django.core.exceptions import ValidationError
    from graphql import (
        DirectiveLocation,
        DocumentNode,
        GraphQLCompositeType,
        GraphQLField,
        GraphQLList,
        GraphQLNonNull,
        GraphQLOutputType,
        GraphQLSchema,
        GraphQLWrappingType,
        Node,
        SelectionNode,
    )
    from graphql.execution.values import NodeWithDirective

    from undine import Field, GQLInfo
    from undine.directives import Directive
    from undine.typing import ModelField


__all__ = [
    "check_directives",
    "get_arguments",
    "get_error_execution_result",
    "get_queried_field_name",
    "get_underlying_type",
    "graphql_error_path",
    "graphql_errors_hook",
    "is_connection",
    "is_edge",
    "is_node_interface",
    "is_page_info",
    "is_relation_id",
    "is_subscription_operation",
    "should_skip_node",
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


def get_field_def(schema: GraphQLSchema, parent_type: GraphQLCompositeType, field_node: FieldNode) -> GraphQLField:
    try:
        from graphql.execution.execute import get_field_def  # noqa: PLC0415

        return get_field_def(schema, parent_type, field_node)

    # graphql-core >= 3.3.0
    except ImportError:
        return schema.get_field(parent_type=parent_type, field_name=field_node.name.value)


async def pre_evaluate_request_user(info: GQLInfo) -> None:
    """
    Fetches the request user from the context and caches it to the request.
    This is a workaround when current user is required in an async event loop,
    but the function itself is not async.
    """
    # '_current_user' would be set by 'django.contrib.auth.middleware.get_user' when calling 'request.user'
    info.context._cached_user = await info.context.auser()  # type: ignore[attr-defined]  # noqa: SLF001


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


def is_subscription_operation(document: DocumentNode, operation_name: str | None = None) -> bool:
    operation_definitions: list[OperationDefinitionNode] = [
        definition_node
        for definition_node in document.definitions
        if isinstance(definition_node, OperationDefinitionNode)
    ]

    if len(operation_definitions) == 0:
        raise GraphQLRequestNoOperationError

    if len(operation_definitions) == 1:
        return operation_definitions[0].operation == OperationType.SUBSCRIPTION

    if operation_name is None:
        raise GraphQLRequestMultipleOperationsNoOperationNameError

    for definition in operation_definitions:
        if definition.name is None or definition.name.value != operation_name:
            continue

        return definition.operation == OperationType.SUBSCRIPTION

    raise GraphQLRequestOperationNotFoundError(operation_name=operation_name)


def should_skip_node(node: NodeWithDirective, variable_values: dict[str, Any]) -> bool:
    skip_args = get_directive_values(GraphQLSkipDirective, node, variable_values)
    if skip_args is not None and skip_args["if"] is True:
        return True

    include_args = get_directive_values(GraphQLIncludeDirective, node, variable_values)
    return include_args is not None and include_args["if"] is False


def is_non_null_default_value(default_value: Any) -> bool:
    return not isinstance(default_value, Hashable) or default_value not in {Undefined, None}


# Misc.


@contextmanager
def graphql_error_path(info: GQLInfo, *, key: str | int | None = None) -> Generator[GQLInfo, None, None]:
    """Context manager that sets the path of all GraphQL errors raised during its context."""
    if key is not None:
        info = GraphQLResolveInfo(  # type: ignore[assignment]
            field_name=info.field_name,
            field_nodes=info.field_nodes,
            return_type=info.return_type,
            parent_type=info.parent_type,
            path=info.path.add_key(key),
            schema=info.schema,
            fragments=info.fragments,
            root_value=info.root_value,
            operation=info.operation,
            variable_values=info.variable_values,
            context=info.context,
            is_awaitable=info.is_awaitable,
        )

    try:
        yield info

    except GraphQLError as error:
        if error.path is None:
            error.path = info.path.as_list()
        raise

    except GraphQLErrorGroup as error_group:
        for err in error_group.flatten():
            if err.path is None:
                err.path = info.path.as_list()
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
        raise GraphQLRequestNoOperationError

    if len(operation_definitions) == 1:
        if operation_definitions[0].operation == OperationType.QUERY:
            return

        raise GraphQLGetRequestNonQueryOperationError

    if operation_name is None:
        raise GraphQLRequestMultipleOperationsNoOperationNameError

    for definition in operation_definitions:
        if definition.name is None or definition.name.value != operation_name:
            continue

        if definition.operation != OperationType.QUERY:
            raise GraphQLGetRequestNonQueryOperationError

        return

    raise GraphQLRequestOperationNotFoundError(operation_name=operation_name)


def get_error_execution_result(error: GraphQLError | GraphQLErrorGroup | list[GraphQLError]) -> ExecutionResult:
    if isinstance(error, list):
        errors = graphql_errors_hook(error)
        return ExecutionResult(data=None, errors=errors)

    if isinstance(error, GraphQLErrorGroup):
        errors = graphql_errors_hook(list(error.flatten()))
        return ExecutionResult(data=None, errors=errors)

    errors = graphql_errors_hook([error])
    return ExecutionResult(data=None, errors=errors)


def graphql_errors_hook(errors: list[GraphQLError]) -> list[GraphQLError]:
    """Handle GraphQL errors before adding them to the response."""
    if not errors:
        return errors

    for error in errors:
        extensions: dict[str, Any] = error.extensions

        if error.original_error is None or isinstance(error.original_error, GraphQLError):
            extensions.setdefault("status_code", HTTPStatus.BAD_REQUEST)
        else:
            extensions.setdefault("status_code", HTTPStatus.INTERNAL_SERVER_ERROR)

        if error.__traceback__ is not None:
            log_traceback(error.__traceback__)

            if undine_settings.INCLUDE_ERROR_TRACEBACK:
                extensions["traceback"] = get_traceback(error.__traceback__)

    # Sort the error list in order to make it deterministic
    errors.sort(key=lambda err: (err.locations or [], err.path or [], err.message))
    return errors


def located_validation_error(
    error: ValidationError,
    nodes: Collection[Node],
    path: list[str | int],
) -> GraphQLErrorGroup:
    """Transform a Django ValidationError into a GraphQL errors for each message in the error."""
    code = getattr(error, "code", "").upper()
    error_messages = get_validation_error_messages(error)

    errors: list[GraphQLError] = []
    for field, messages in error_messages.items():
        for message in messages:
            error_path = path.copy()
            if field:
                error_path += field.split(".")

            extensions: dict[str, Any] = {"status_code": HTTPStatus.BAD_REQUEST}
            if code:
                extensions["error_code"] = code

            graphql_error = GraphQLError(message=message, nodes=nodes, path=error_path, extensions=extensions)
            errors.append(graphql_error)

    return GraphQLErrorGroup(errors=errors)
