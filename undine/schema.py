from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any, Literal, Self

from graphql import (
    ExecutionContext,
    ExecutionResult,
    GraphQLArgumentMap,
    GraphQLDirective,
    GraphQLError,
    GraphQLField,
    GraphQLFieldResolver,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLSchema,
    OperationType,
    Undefined,
    execute,
    get_operation_ast,
    parse,
    specified_directives,
    specified_rules,
    validate,
    validate_schema,
)

from undine.converters import (
    convert_entrypoint_ref_to_resolver,
    convert_to_graphql_argument_map,
    convert_to_graphql_type,
    is_many,
)
from undine.errors.error_handlers import raised_exceptions_as_execution_results
from undine.errors.exceptions import GraphQLInvalidOperationError, MissingEntrypointRefError
from undine.parsers import parse_class_variable_docstrings, parse_description
from undine.settings import undine_settings
from undine.utils.graphql import add_default_status_codes, get_or_create_object_type, maybe_list_or_non_null
from undine.utils.reflection import cache_signature_if_function, get_members
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Collection

    from undine.dataclasses import GraphQLParams
    from undine.typing import EntrypointRef

__all__ = [
    "Entrypoint",
    "create_schema",
    "execute_graphql",
]


class Entrypoint:
    """
    A class for creating new fields in the root operation types of the GraphQL schema.
    These can be used to make queries or make mutations.

    >>> class Query:
    >>>     @Entrypoint
    >>>     def testing(self, name: str) -> str:
    >>>         return f"Hello, {name}!"
    """

    def __init__(
        self,
        ref: EntrypointRef = Undefined,
        *,
        many: bool = False,
        max_complexity: int = Undefined,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        Create a new `Entrypoint`.

        :param ref: The reference to use for the `Entrypoint`.
        :param many: Whether the `Entrypoint` should return a non-null list of the referenced type.
        :param max_complexity: Maximum number of relations that are allowed to be queried from this `Entrypoint`.
        :param description: Description for the `Entrypoint`.
        :param deprecation_reason: If the `Entrypoint` is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the `Entrypoint`.
        """
        self.ref = cache_signature_if_function(ref, depth=1)
        self.many = many
        self.max_complexity = max_complexity or undine_settings.OPTIMIZER_MAX_COMPLEXITY
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.ENTRYPOINT_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type, name: str) -> None:
        # Called as part of the descriptor protocol if this `Entrypoint` is assigned
        # to a variable in the class body of a `Query` or `Mutation` class.
        self.owner = owner
        self.name = name

        if self.ref is Undefined:
            raise MissingEntrypointRefError(name=name, cls=owner)

        if isinstance(self.ref, FunctionType):
            self.many = is_many(self.ref)
        if self.description is Undefined:
            variable_docstrings = parse_class_variable_docstrings(self.owner)
            self.description = variable_docstrings.get(self.name, Undefined)
            if self.description is Undefined:
                self.description = parse_description(self.ref)

    def __call__(self, ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Entrypoint()"""
        self.ref = cache_signature_if_function(ref, depth=1)
        return self

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref})>"

    def as_graphql_field(self) -> GraphQLField:
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(),
            resolve=self.get_resolver(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLOutputType:
        graphql_type, nullable = convert_to_graphql_type(self.ref, return_nullable=True)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=not nullable)

    def get_field_arguments(self) -> GraphQLArgumentMap:
        return convert_to_graphql_argument_map(self.ref, many=self.many, entrypoint=True)

    def get_resolver(self) -> GraphQLFieldResolver:
        return convert_entrypoint_ref_to_resolver(self.ref, caller=self)


def create_schema(
    *,
    query_class: type,
    mutation_class: type | None = None,
    schema_description: str | None = None,
    query_extensions: dict[str, Any] | None = None,
    mutation_extensions: dict[str, Any] | None = None,
    schema_extensions: dict[str, Any] | None = None,
    additional_types: Collection[GraphQLNamedType] | None = None,
    additional_directives: Collection[GraphQLDirective] | None = None,
) -> GraphQLSchema:
    """Creates the GraphQL schema."""

    def create_type(cls: type | None, extensions: dict[str, Any] | None = None) -> GraphQLObjectType | None:
        if cls is None:
            return None

        return get_or_create_object_type(
            name=cls.__name__,
            fields={
                to_schema_name(name): entrypoint.as_graphql_field()
                for name, entrypoint in get_members(cls, Entrypoint).items()
            },
            description=get_docstring(cls),
            extensions=extensions,
        )

    query_object_type = create_type(query_class, query_extensions)
    mutation_object_type = create_type(mutation_class, mutation_extensions)

    return GraphQLSchema(
        query=query_object_type,
        mutation=mutation_object_type,
        types=additional_types,
        directives=(*specified_directives, *additional_directives) if additional_directives else None,
        description=schema_description,
        extensions=schema_extensions,
    )


class UndineExecutionContext(ExecutionContext):
    """Custom GraphQL execution context class."""

    @staticmethod
    def build_response(data: dict[str, Any] | None, errors: list[GraphQLError]) -> ExecutionResult:
        return ExecutionContext.build_response(data, add_default_status_codes(errors))


@raised_exceptions_as_execution_results
def execute_graphql(params: GraphQLParams, method: Literal["GET", "POST"], context_value: Any) -> ExecutionResult:
    """
    Executes a GraphQL query.

    :param params: GraphQL query parameters including the query, variables, and operation name.
    :param method: The HTTP method of the GraphQL request.
    :param context_value: The context value for the GraphQL execution.
    """
    schema_validation_errors = validate_schema(undine_settings.SCHEMA)
    if schema_validation_errors:
        return ExecutionResult(errors=add_default_status_codes(schema_validation_errors))

    try:
        document = parse(
            source=params.query,
            no_location=undine_settings.NO_ERROR_LOCATION,
            max_tokens=undine_settings.MAX_TOKENS,
        )
    except GraphQLError as parse_error:
        return ExecutionResult(errors=add_default_status_codes([parse_error]))

    if method == "GET":
        operation_node = get_operation_ast(document, params.operation_name)
        if getattr(operation_node, "operation", None) != OperationType.QUERY:
            return ExecutionResult(errors=[GraphQLInvalidOperationError()])

    validation_errors = validate(
        schema=undine_settings.SCHEMA,
        document_ast=document,
        rules=(*specified_rules, *undine_settings.ADDITIONAL_VALIDATION_RULES),
        max_errors=undine_settings.MAX_ERRORS,
    )
    if validation_errors:
        return ExecutionResult(errors=add_default_status_codes(validation_errors))

    return execute(
        schema=undine_settings.SCHEMA,
        document=document,
        root_value=undine_settings.ROOT_VALUE,
        context_value=context_value,
        variable_values=params.variables,
        operation_name=params.operation_name,
        middleware=undine_settings.MIDDLEWARE,
        execution_context_class=undine_settings.EXECUTION_CONTEXT_CLASS,
    )
