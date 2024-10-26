from __future__ import annotations

from string import Formatter
from typing import TYPE_CHECKING, Any, ClassVar, Collection

from graphql import GraphQLError

from undine.errors import error_codes

if TYPE_CHECKING:
    from graphql import GraphQLErrorExtensions, Node, Source

__all__ = [
    "FunctionDispatcherError",
    "FuntionSignatureParsingError",
    "GraphQLConversionError",
    "GraphQLConversionError",
    "GraphQLStatusError",
    "GraphQLStatusError",
    "InvalidParserError",
    "MismatchingModelError",
    "MissingFunctionAnnotationsError",
    "MissingFunctionReturnTypeError",
    "MissingModelError",
    "ModelFieldDoesNotExistError",
    "ModelFieldNotARelationError",
    "NoFunctionParametersError",
    "OptimizerError",
    "RegistryDuplicateError",
    "SchemaNameValidationError",
    "TypeRegistryMissingTypeError",
    "UndineError",
]


class ErrorMessageFormatter(Formatter):
    """Formatter for error strings."""

    def format_field(self, value: Any, format_spec: str) -> str:  # noqa: PLR0911
        from undine.utils.text import comma_sep_str, dotpath  # noqa: PLC0415

        if format_spec == "dotpath":
            return dotpath(value)
        if format_spec == "module":
            return value.__module__
        if format_spec == "name":
            return value.__name__
        if format_spec == "qualname":
            return value.__qualname__
        if format_spec == "comma_sep_or":
            return comma_sep_str(value, last_sep="or", quote=True)
        if format_spec == "comma_sep_and":
            return comma_sep_str(value, last_sep="and", quote=True)

        return super().format_field(value, format_spec)


# Undine Errors


class UndineError(Exception):
    """Base class for all undine errors."""

    msg: ClassVar[str] = ""
    error_formatter = ErrorMessageFormatter()

    def __init__(self, msg: str = "", **kwargs: Any) -> None:
        msg = self.error_formatter.format(msg or self.msg, **kwargs)
        super().__init__(msg)


class FuntionSignatureParsingError(UndineError):
    """Error raised if a function is missing type annotations for its parameters."""

    msg = (
        "Name '{name}' is not defined in module '{func:module}'. "
        "Check if it's inside a `if TYPE_CHECKING` block. '{name}' needs to be "
        "available during runtime so that signature of '{func:qualname}' can be inspected."
    )


class InvalidParserError(UndineError):
    """Error raised when an invalid dosctring parser is provided."""

    msg = "'{cls:dotpath}' does not implement 'DocstringParserProtocol'."


class MismatchingModelError(UndineError):
    """
    Error raised if provided model for `FilterSet` or `OrderSet`
    doesn't match model of the given `QueryType`.
    """

    msg = "'{cls}' model '{given_model:dotpath}' does not match '{type}' model'{expected_model:dotpath}'."


class MissingEntrypointRefError(UndineError):
    """Error raised when an entrypoint is missing a reference."""

    msg = "Entrypoint '{name}' in class '{cls}' must have a reference."


class MissingFunctionAnnotationsError(UndineError):
    """Error raised if a function is missing type annotations for its parameters."""

    msg = "Missing type hints for parameters {missing:comma_sep_or} in function '{func:dotpath}'."


class MissingFunctionReturnTypeError(UndineError):
    """Error raised if a function does not contain a parameter to parse type from."""

    msg = "Missing type hint for return value in function '{func:dotpath}'."


class MissingModelError(UndineError):
    """Error raised if no model is provided to `QueryType`, `FilterSet`, or `OrderSet`."""

    msg = "{name} is missing `model` keyword argument in its class definition: `class {name}({cls}, model=MyModel)`."


class ModelFieldDoesNotExistError(UndineError):
    """Error raised if a field does not exist in the given model."""

    msg = "Field '{field}' does not exist in model '{model:dotpath}'."


class ModelFieldNotARelationError(UndineError):
    """Error raised if a field is not a relation in the given model."""

    msg = "Field '{field}' is not a relation in model '{model:dotpath}'."


class NoFunctionParametersError(UndineError):
    """Error raised if a function does not contain a parameter to parse type from."""

    msg = "Function {func:dotpath} must have at least one argument."


class OptimizerError(UndineError):
    """Error raised during the optimization compilation process."""


class PaginationArgumentValidationError(UndineError):
    """Error raised for invalid pagination arguments."""


class SchemaNameValidationError(UndineError):
    """Error raised if GraphQL schema field name validation fails."""

    msg = (
        "'{name}' is not not an allowed name. "
        "Names must be in 'snake_case', all lower case, and cannot begin or end with an underscore. "
        "Also, any underscores must be followed by a letter due ambiguousness when converting "
        "values like 'the_1st' vs 'the1st' to 'camelCase' and then back to 'snake_case'."
    )


class FunctionDispatcherError(UndineError):
    """Error raised for `FunctionDispatcher` errors."""


class RegistryDuplicateError(UndineError):
    """Error raised if trying to register a value for the same key twice."""

    msg = "'{registry_name}' alrady contains a value for '{key}': '{value}'"


class TypeRegistryMissingTypeError(UndineError):
    """Error raised when a Regsitry doesn't contain an entry for a given key."""

    msg = "'{registry_name}' doesn't contain an entry for '{key}'"


# GraphQL Errors


class GraphQLStatusError(GraphQLError):
    """Base error for GraphQL error in Undine."""

    msg: ClassVar[str] = ""
    status: ClassVar[int] = 500
    code: ClassVar[str | None] = None
    error_formatter = ErrorMessageFormatter()

    def __init__(  # noqa: PLR0913
        self,
        message: str = "",
        *,
        status: int | None = None,
        code: str | None = None,
        nodes: Collection[Node] | Node | None = None,
        source: Source | None = None,
        positions: Collection[int] | None = None,
        path: Collection[str | int] | None = None,
        original_error: Exception | None = None,
        extensions: GraphQLErrorExtensions | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the GraphQL Error with some extra information.

        :param message: A message describing the Error for debugging purposes.
        :param status: HTTP status code.
        :param code: Unique error code.
        :param nodes: A list of GraphQL AST Nodes corresponding to this error
        :param source: The source GraphQL document for the first location of this error.
        :param positions: A list of character offsets within the source GraphQL document which correspond
                          to this error.
        :param path: A list of field names and array indexes describing the JSON-path into the execution
                     response which corresponds to this error.
        :param original_error: The original error thrown from a field resolver during execution.
        :param extensions: Extension fields to add to the formatted error.
        """
        status = status or self.status
        code = code or self.code
        message = self.error_formatter.format(message or self.msg, **kwargs)
        extensions = extensions or {}
        extensions["status_code"] = status
        if code is not None:
            extensions["error_code"] = code

        super().__init__(
            message=message,
            nodes=nodes,
            source=source,
            positions=positions,
            path=path,
            original_error=original_error,
            extensions=extensions,
        )


class GraphQLCantCreateEnumError(GraphQLStatusError):
    """Error raised when trying to create an enum with no choices."""

    msg = "Cannot create GraphQL Enum '{name}' with zero values."
    status = 400
    code = error_codes.GRAPHQL_CANT_CREATE_ENUM


class GraphQLConversionError(GraphQLStatusError):
    """Error raised when a value cannot be converted to a GraphQL type."""

    msg = "{typename} cannot represent value {value}: {error}"
    status = 400
    code = error_codes.GRAPHQL_CONVERSION_ERROR


class GraphQLDecodeError(GraphQLStatusError):
    """Error raised when a request content cannot be decoded to python data."""

    status = 400
    code = error_codes.DECODING_ERROR


class GraphQLDuplicateTypeError(GraphQLStatusError):
    """Error raised when trying to create a type in the GraphQL schema with the same name as an existing type."""

    msg = (
        "GraphQL schema already has a known type with the name '{name}': '{type_existing:dotpath}'. "
        "Cannot add a new type '{type_new:dotpath}'."
    )
    status = 400
    code = error_codes.GRAPHQL_DUPLICATE_ENUM


class GraphQLEmptyQueryError(GraphQLStatusError):
    """Error raised when parsing file upload data doesn't contain a `map` files mapping."""

    msg = "Requests must contain a `query` string describing the graphql document."
    status = 400
    code = error_codes.EMPTY_QUERY


class GraphQLFileParsingError(GraphQLStatusError):
    """Error raised when parsing file data for mutation input fails."""

    status = 400
    code = error_codes.FILE_NOT_FOUND


class GraphQLInvalidInputDataError(GraphQLStatusError):
    """Error raised when a request content cannot be decoded to python data."""

    msg = "Invalid input data for field '{field_name}': {data!r}"
    status = 400
    code = error_codes.INVALID_INPUT_DATA


class GraphQLInvalidManyRelatedFieldError(GraphQLStatusError):
    """Error raised when trying to resolve a many-related field that doesn't resolve to a related manager."""

    msg = (
        "Trying to resolve field '{field_name}' on model '{model:dotpath}' as a many-related field, "
        "but field doesn't resolve into a related manager. Got '{value}' instead."
    )
    status = 400
    code = error_codes.INVALID_MANY_RELATED_FIELD


class GraphQLInvalidOperationError(GraphQLStatusError):
    """Error raised when user tries to execute non-query operations on a GET request."""

    msg = "Only query operations are allowed on GET requests."
    status = 405


class GraphQLBadInputDataError(GraphQLStatusError):
    """Error raised when a request content is not correct according to the GraphQL schema."""

    msg = (
        "Input data contains data for field '{field_name}' but MutationType '{mutation_type:dotpath}' "
        "doesn't have an input with that name."
    )
    status = 400
    code = error_codes.INVALID_INPUT_DATA


class GraphQLMissingContentTypeError(GraphQLStatusError):
    """Error raised when a request is made wihtout a content type."""

    msg = "Must provide a 'Content-Type' header."
    status = 415
    code = error_codes.CONTENT_TYPE_MISSING


class GraphQLMissingFileMapError(GraphQLStatusError):
    """Error raised when parsing file upload data doesn't contain a `map` files mapping."""

    msg = "File upload must contain an `map` value."
    status = 400
    code = error_codes.MISSING_FILE_MAP


class GraphQLMissingLookupFieldError(GraphQLStatusError):
    """Error raised when a lookup field is missing from the mutation input data for fetching the mutated instance."""

    msg = (
        "Input data is missing value for the mutation lookup field '{key}'. "
        "Cannot fetch '{model:dotpath}' object for mutation."
    )
    status = 400
    code = error_codes.LOOKUP_VALUE_MISSING


class GraphQLMissingOperationsError(GraphQLStatusError):
    """Error raised when parsing file upload data doesn't contain an `operations` data mapping."""

    msg = "File upload must contain an `operations` value."
    status = 400
    code = error_codes.MISSING_OPERATIONS


class GraphQLModelConstaintViolationError(GraphQLStatusError):
    """Error raised when a request is made with an unsupported content type."""

    status = 400
    code = error_codes.MODEL_CONSTRAINT_VIOLATION


class GraphQLModelNotFoundError(GraphQLStatusError):
    """Error raised when a model lookup fails to find a matching row."""

    msg = "Lookup `{key}={value!r}` on model `{model:dotpath}` did not match any row."
    status = 404
    code = error_codes.MODEL_NOT_FOUND


class GraphQLMultipleObjectsFoundError(GraphQLStatusError):
    """Error raised when a model lookup finds more than one matching row."""

    msg = "Lookup `{key}={value!r}` on model `{model:dotpath}` matched more than one row."
    status = 500
    code = error_codes.MODEL_MULTIPLE_OBJECTS


class GraphQLUnsupportedContentTypeError(GraphQLStatusError):
    """Error raised when a request is made with an unsupported content type."""

    msg = "'{content_type}' is not a supported content type."
    status = 415
    code = error_codes.UNSUPPORTED_CONTENT_TYPE
