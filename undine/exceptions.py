from __future__ import annotations

from http import HTTPStatus
from string import Formatter
from typing import TYPE_CHECKING, Any, ClassVar, Self

from graphql import GraphQLError

from undine.typing import UndineErrorCodes

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Sequence

    from graphql import GraphQLErrorExtensions, Node, Source


class ErrorMessageFormatter(Formatter):
    """Formatter for error strings."""

    def format_field(self, value: Any, format_spec: str) -> str:
        from undine.utils.text import comma_sep_str, dotpath  # noqa: PLC0415

        if format_spec == "dotpath":
            return dotpath(value)
        if format_spec == "module":
            return value.__module__
        if format_spec == "name":
            return value.__name__
        if format_spec == "qualname":
            return value.__qualname__
        if format_spec == "type":
            return type(value).__name__
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


class UndineErrorGroup(ExceptionGroup):
    """Base class for all undine exception groups."""

    msg: ClassVar[str] = ""
    error_formatter = ErrorMessageFormatter()

    def __new__(cls, errors: Sequence[Exception], *, msg: str = "", **kwargs: Any) -> Self:
        msg = cls.error_formatter.format(msg or cls.msg, **kwargs)
        return super().__new__(UndineErrorGroup, msg, errors)  # type: ignore[return-value]

    def __init__(self, errors: Sequence[Exception], *, msg: str = "", **kwargs: Any) -> None:
        super().__init__(msg, errors)

    def flatten(self) -> Generator[Exception, None, None]:
        """Flattened the errors inside the `UndineErrorGroup`."""
        for error in self.exceptions:
            if isinstance(error, UndineErrorGroup):
                yield from error.flatten()
            elif isinstance(error, Exception):
                yield error


class DirectiveLocationError(UndineError):
    """Error raised if Directive is passed to a location it cannot be used in."""

    msg = "Directive {directive!r} is not allowed in {location.name!r}"


class EmptyFilterResult(UndineError):  # noqa: N818
    """Error that should be raised when using a filter should result in an empty queryset."""

    msg = "Filter result should be null."


class ExpressionMultipleOutputFieldError(UndineError):
    """Error raised if no output field cannot be determined for an expression."""

    msg = (
        "Could not determine an output field for expression {expr!r}. "
        "Got multiple possible output fields: {output_fields}."
    )


class ExpressionNoOutputFieldError(UndineError):
    """Error raised if no output field cannot be determined for an expression."""

    msg = (
        "Could not determine an output field for expression {expr!r}. "
        "No output field found from any source expressions."
    )


class FunctionSignatureParsingError(UndineError):
    """Error raised if a function is missing type annotations for its parameters."""

    msg = (
        "Type '{name}' is not defined in module '{func:module}'. "
        "Check if it's inside a `if TYPE_CHECKING` block or another class/function. "
        "The type needs to be available at the runtime so that the signature of '{func:qualname}' can be inspected."
    )


class InvalidInputMutationTypeError(UndineError):
    """Error raised when trying to create an `Input` using a `MutationType` with a `kind` other than 'related'."""

    msg = (
        "MutationType '{ref:dotpath}' is a '{kind}' MutationType, "
        "but only 'related' MutationTypes can be used as Inputs on other MutationTypes."
    )


class InvalidDocstringParserError(UndineError):
    """Error raised when an invalid docstring parser is provided."""

    msg = "'{cls:dotpath}' does not implement 'DocstringParserProtocol'."


class InvalidEntrypointMutationTypeError(UndineError):
    """Error raised when trying to create an `Entrypoint` using a `MutationType` with an unknown `kind`."""

    msg = (
        "MutationType '{ref:dotpath}' is a '{kind}' MutationType, "
        "but only 'create', 'update', 'delete', or 'custom' MutationTypes can be used in Entrypoints."
    )


class MismatchingModelError(UndineError):
    """
    Error raised if provided model for `FilterSet` or `OrderSet`
    doesn't match model of the given `QueryType`.
    """

    msg = "'{name}' model '{given_model:dotpath}' does not match '{target}' model '{expected_model:dotpath}'."


class MissingCalculationReturnTypeError(UndineError):
    """Error raised if a calculation class doesn't define a return type."""

    msg = (
        "'{name}' must define the calculation return type using the Generic type argument: "
        "e.g. `class {name}(Calculation[int]):`"
    )


class MissingEntrypointRefError(UndineError):
    """Error raised when an entrypoint is missing a reference."""

    msg = "Entrypoint '{name}' in class '{cls:dotpath}' must have a reference."


class MissingFunctionAnnotationsError(UndineError):
    """Error raised if a function is missing type annotations for its parameters."""

    msg = "Missing type hints for parameters {missing:comma_sep_and} in function '{func:dotpath}'."


class MissingFunctionReturnTypeError(UndineError):
    """Error raised if a function does not contain a parameter to parse type from."""

    msg = "Missing type hint for return value in function '{func:dotpath}'."


class MissingDirectiveArgumentError(UndineError):
    """Error raised if a directive argument is missing."""

    msg = "Missing directive argument '{name}' for directive '{directive:dotpath}'."


class MissingDirectiveLocationsError(UndineError):
    """Error raised if no locations are provided to `Directive`."""

    msg = (
        "'{name}' is missing `locations` keyword argument in its class definition: "
        "e.g. `class {name}(Directive, locations=[DirectiveLocation.FIELD_DEFINITION])`."
    )


class MissingModelGenericError(UndineError):
    """Error raised if no model is provided to `QueryType`, `MutationType`, `FilterSet`, or `OrderSet`."""

    msg = "'{name}' is missing its generic types: `class {name}({cls}[MyModel])`."


class MissingUnionQueryTypeGenericError(UndineError):
    """Error raised if no models are provided to `UnionType`."""

    msg = "'{name}' is missing its generic types: `class {name}(UnionType[QueryType1, QueryType2])`."


class ModelFieldError(UndineError): ...


class ModelFieldDoesNotExistError(ModelFieldError):
    """Error raised if a field does not exist in the given model."""

    msg = "Field '{field}' does not exist in model '{model:dotpath}'."


class ModelFieldNotARelationError(ModelFieldError):
    """Error raised if a field is not a relation in the given model."""

    msg = "Field '{field}' is not a relation in model '{model:dotpath}'."


class NoFunctionParametersError(UndineError):
    """Error raised if a function does not contain a parameter to parse type from."""

    msg = "Function '{func:dotpath}' must have at least one argument."


class FunctionDispatcherError(UndineError):
    """Error raised for `FunctionDispatcher` errors."""


class FunctionDispatcherImplementationNotFoundError(FunctionDispatcherError):
    """Error raised when `FunctionDispatcher` cannot find an implementation for a given key."""

    msg = "'{name}' doesn't contain an implementation for {key!r} (type: {cls:dotpath})."


class FunctionDispatcherImproperLiteralError(FunctionDispatcherError):
    """
    Error raised when a trying to register an implementation for a `FunctionDispatcher`
    with a Literal that has an invalid value.
    """

    msg = "Literal argument must be a string, integer, bytes, boolean, enum, or None, got {arg!r}."


class FunctionDispatcherNoArgumentAnnotationError(FunctionDispatcherError):
    """
    Error raised when a trying to register an implementation for a `FunctionDispatcher`
    with a function that doesn't have a type hint for its first argument.
    """

    msg = (
        "Function '{func_name}' must have a type hint for its first argument so that it can be registered for '{name}'."
    )


class FunctionDispatcherNoArgumentsError(FunctionDispatcherError):
    """
    Error raised when a trying to register an implementation for a `FunctionDispatcher`
    with a function that doesn't have any arguments.
    """

    msg = "Function '{func_name}' must have at least one argument so that it can be registered for '{name}'."


class FunctionDispatcherNonRuntimeProtocolError(FunctionDispatcherError):
    """
    Error raised when a trying to register an implementation for a `FunctionDispatcher`
    with a protocol that hasn't been decorated with `@runtime_checkable`.
    """

    msg = "Protocol '{name}' is not a runtime checkable protocol."


class FunctionDispatcherRegistrationError(FunctionDispatcherError):
    """
    Error raised when a trying to register an implementation for a `FunctionDispatcher`
    that is something other than a function.
    """

    msg = "Can only register functions with '{name}'. Got {value!r}."


class FunctionDispatcherUnionTypeError(FunctionDispatcherError):
    """
    Error raised when a trying to register an implementation for a `FunctionDispatcher`
    with a Union type that has more than one non-null type.
    """

    msg = "Union type must have a single non-null type argument, got {args}."


class FunctionDispatcherUnknownArgumentError(FunctionDispatcherError):
    """
    Error raised when a trying to register an implementation for a `FunctionDispatcher`
    with an unknown argument type.
    """

    msg = "Unknown argument: {annotation!r}"


class RegistryDuplicateError(UndineError):
    """Error raised if trying to register a value for the same key twice."""

    msg = "'{registry_name}' already contains a value for '{key}': '{value}'"


class RegistryMissingTypeError(UndineError):
    """Error raised when a Registry doesn't contain an entry for a given key."""

    msg = "'{registry_name}' doesn't contain an entry for '{key}'"


class UnexpectedDirectiveArgumentError(UndineError):
    """Error raised if a directive argument is unexpected."""

    msg = "Unexpected directive arguments for directive '{directive:dotpath}': {kwargs}."


# GraphQL Errors


class GraphQLStatusError(GraphQLError):
    """Base error for GraphQL error in Undine."""

    msg: ClassVar[str] = ""
    status: ClassVar[int] = HTTPStatus.INTERNAL_SERVER_ERROR
    code: ClassVar[str | None] = None
    error_formatter = ErrorMessageFormatter()

    def __init__(
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


class GraphQLErrorGroup(ExceptionGroup):
    """Exception group for GraphQL errors."""

    msg: ClassVar[str] = ""
    error_formatter = ErrorMessageFormatter()

    # Need to override both __new__ and __init__ so that keyword arguments can be used.

    def __new__(cls, errors: Sequence[GraphQLError | GraphQLErrorGroup], *, msg: str = "", **kwargs: Any) -> Self:
        msg = cls.error_formatter.format(msg or cls.msg, **kwargs)
        return super().__new__(GraphQLErrorGroup, msg, errors)  # type: ignore[return-value]

    def __init__(self, errors: Sequence[GraphQLError | GraphQLErrorGroup], *, msg: str = "", **kwargs: Any) -> None:
        super().__init__(msg, errors)

    def __str__(self) -> str:
        return "\n\n".join(str(error) for error in self.flatten())

    def flatten(self) -> Generator[GraphQLError, None, None]:
        """Flattened the errors inside the `GraphQLExceptionGroup`."""
        for error in self.exceptions:
            if isinstance(error, GraphQLErrorGroup):
                yield from error.flatten()
            elif isinstance(error, GraphQLError):
                yield error

    def located_by(self, error: GraphQLError) -> Self:
        """Set location information to all errors inside the `GraphQLExceptionGroup` based on the given error."""
        for err in self.flatten():
            if not err.source:
                err.source = error.source
            if not err.positions:
                err.positions = error.positions
            if not err.path:
                err.path = error.path
            if not err.nodes:
                err.nodes = error.nodes
        return self


class GraphQLDuplicateTypeError(GraphQLStatusError):
    """Error raised when trying to create a type in the GraphQL schema with the same name as an existing type."""

    msg = (
        "GraphQL schema already has a known type with the name '{name}': '{type_existing!r}'. "
        "Cannot add a new type '{type_new!r}'."
    )
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.DUPLICATE_TYPE


class GraphQLFilePlacingError(GraphQLStatusError):
    """Error raised when placing uploaded files to request data fails."""

    msg = "Value '{value}' in file map does not lead to a null value."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.FILE_NOT_FOUND


class GraphQLFileNotFoundError(GraphQLStatusError):
    """Error raised when a file is not found in the GraphQL request files map."""

    msg = "File for path '{key}' not found in request files."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.FILE_NOT_FOUND


class GraphQLGetRequestMultipleOperationsNoOperationNameError(GraphQLStatusError):
    """
    Error raised when user tries to execute multiple operations
    through an HTTP GET request without an operation name.
    """

    msg = "Must provide operation name if query contains multiple operations."
    status = HTTPStatus.METHOD_NOT_ALLOWED
    code = UndineErrorCodes.MISSING_OPERATION_NAME


class GraphQLGetRequestNonQueryOperationError(GraphQLStatusError):
    """Error raised when user tries to execute non-query operations through an HTTP GET request."""

    msg = "Only query operations are allowed on GET requests."
    status = HTTPStatus.METHOD_NOT_ALLOWED
    code = UndineErrorCodes.INVALID_OPERATION_FOR_METHOD


class GraphQLGetRequestNoOperationError(GraphQLStatusError):
    """Error raised when no operation definition can be found in the request."""

    msg = "Must provide an operation."
    status = HTTPStatus.METHOD_NOT_ALLOWED
    code = UndineErrorCodes.NO_OPERATION


class GraphQLGetRequestOperationNotFoundError(GraphQLStatusError):
    """Error raised when operation matching given operation name cannot be found in the request."""

    msg = "Unknown operation named '{operation_name}'."
    status = HTTPStatus.METHOD_NOT_ALLOWED
    code = UndineErrorCodes.OPERATION_NOT_FOUND


class GraphQLInvalidInputDataError(GraphQLStatusError):
    """Error raised when a mutation receives invalid input data for some input."""

    msg = "Invalid input data for field {field_name!r}: {data!r}"
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.INVALID_INPUT_DATA


class GraphQLInvalidOrderDataError(GraphQLStatusError):
    """Error raised when a mutation receives invalid order data for an OrderSet."""

    msg = (
        "Order data contains ordering value '{enum_value}' but OrderSet '{orderset:dotpath}' "
        "doesn't have support an order with that name."
    )
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.INVALID_ORDER_DATA


class GraphQLMissingCalculationArgumentError(GraphQLStatusError):
    """Error raised if a calculation argument is missing."""

    msg = "Missing calculation argument '{arg}' for calculation '{name}'."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MISSING_CALCULATION_ARGUMENT


class GraphQLMissingContentTypeError(GraphQLStatusError):
    """Error raised when a request is made without a content type."""

    msg = "Must provide a 'Content-Type' header."
    status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    code = UndineErrorCodes.CONTENT_TYPE_MISSING


class GraphQLMissingFileMapError(GraphQLStatusError):
    """Error raised when parsing file upload data doesn't contain a `map` files mapping."""

    msg = "File upload must contain an `map` value."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MISSING_FILE_MAP


class GraphQLMissingLookupFieldError(GraphQLStatusError):
    """Error raised when a lookup field is missing from the mutation input data for fetching the mutated instance."""

    msg = (
        "Input data is missing value for the mutation lookup field '{key}'. "
        "Cannot fetch '{model:dotpath}' object for mutation."
    )
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.LOOKUP_VALUE_MISSING


class GraphQLMissingOperationsError(GraphQLStatusError):
    """Error raised when parsing file upload data doesn't contain an `operations` data mapping."""

    msg = "File upload must contain an `operations` value."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MISSING_OPERATIONS


class GraphQLMissingDocumentIDError(GraphQLStatusError):
    """Error raised if persisted document id are missing from the request."""

    msg = "Request data must contain a `documentId` string identifying a persisted document."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MISSING_GRAPHQL_DOCUMENT_PARAMETER


class GraphQLMissingQueryError(GraphQLStatusError):
    """Error raised when query string is missing from the request."""

    msg = "Request data must contain a `query` string describing the graphql document."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MISSING_GRAPHQL_QUERY_PARAMETER


class GraphQLMissingQueryAndDocumentIDError(GraphQLStatusError):
    """Error raised both neither the query string and persisted document id are missing from the request."""

    msg = (
        "Request data must contain either a `query` string describing the graphql document "
        "or a `documentId` string identifying a persisted document."
    )
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MISSING_GRAPHQL_QUERY_AND_DOCUMENT_PARAMETERS


class GraphQLModelConstraintViolationError(GraphQLStatusError):
    """Error raised when a request is made with an unsupported content type."""

    msg = "Model constraint violation"
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MODEL_CONSTRAINT_VIOLATION


class GraphQLModelNotFoundError(GraphQLStatusError):
    """Error raised when a model lookup fails to find a matching row."""

    msg = "Primary key {pk!r} on model '{model:dotpath}' did not match any row."
    status = HTTPStatus.NOT_FOUND
    code = UndineErrorCodes.MODEL_NOT_FOUND


class GraphQLModelsNotFoundError(GraphQLStatusError):
    """Error raised when model lookup doesn't find expected number of matching rows."""

    msg = "Primary keys {missing:comma_sep_and} on model '{model:dotpath}' did not match any row."
    status = HTTPStatus.NOT_FOUND
    code = UndineErrorCodes.MODEL_NOT_FOUND


class GraphQLMutationInputNotFoundError(GraphQLStatusError):
    """Error raised when mutation receives input data for a field that doesn't exist in the MutationType."""

    msg = (
        "Input data contains data for field '{field_name}' but MutationType '{mutation_type:dotpath}' "
        "doesn't have an input with that name."
    )
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.INVALID_INPUT_DATA


class GraphQLMutationInstanceLimitError(GraphQLStatusError):
    """Error raised when mutation contains too many objects."""

    msg = "Cannot mutate more than {limit} objects in a single mutation."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MUTATION_TOO_MANY_OBJECTS


class GraphQLMutationTreeModelMismatchError(GraphQLStatusError):
    """Error raised when trying to merge mutation nodes with different models."""

    msg = "Cannot merge MutationNodes for different models: '{model_1:dotpath}' and '{model_2:dotpath}'."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MUTATION_TREE_MODEL_MISMATCH


class GraphQLNodeIDFieldTypeError(GraphQLStatusError):
    """Error raised when a Node request `id` field type is not the Global ID type."""

    msg = "The 'id' field of the object type '{typename}' must be of type 'ID' to comply with the 'Node' interface."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.NODE_ID_NOT_GLOBAL_ID


class GraphQLNodeInterfaceMissingError(GraphQLStatusError):
    """Error raised when a Node request ObjectType does not implement the Node interface."""

    msg = "Object type '{typename}' must implement the 'Node' interface."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.NODE_INTERFACE_MISSING


class GraphQLNodeInvalidGlobalIDError(GraphQLStatusError):
    """Error raised when a Node request `id` is not a valid Global ID."""

    msg = "'{value}' is not a valid Global ID."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.NODE_INVALID_GLOBAL_ID


class GraphQLNodeMissingIDFieldError(GraphQLStatusError):
    """Error raised when a Node request ObjectType does not contain an `id` field."""

    msg = "The object type '{typename}' doesn't have an 'id' field."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.NODE_QUERY_TYPE_ID_FIELD_MISSING


class GraphQLNodeObjectTypeMissingError(GraphQLStatusError):
    """Error raised when a Node request `id` is for an unrecognized ObjectType."""

    msg = "Object type '{typename}' does not exist in schema."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.NODE_MISSING_OBJECT_TYPE


class GraphQLNodeQueryTypeMissingError(GraphQLStatusError):
    """Error raised when a Node request ObjectType does not contain an extension for it's undine QueryType."""

    msg = "Cannot find undine QueryType from object type '{typename}'."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.NODE_QUERY_TYPE_MISSING


class GraphQLNodeTypeNotObjectTypeError(GraphQLStatusError):
    """Error raised when a Node request `id` is for an unrecognized ObjectType."""

    msg = "Node ID type '{typename}' is not an object type."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.NODE_TYPE_NOT_OBJECT_TYPE


class GraphQLNoExecutionResultError(GraphQLStatusError):
    """Error raised when no execution result exists after the GraphQL execution."""

    msg = "No execution result after GraphQL operation."
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    code = UndineErrorCodes.NO_EXECUTION_RESULT


class GraphQLOptimizerError(GraphQLStatusError):
    """Error raised during the optimization compilation process."""

    msg = "GraphQL optimization failed."
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    code = UndineErrorCodes.OPTIMIZER_ERROR


class GraphQLPaginationArgumentValidationError(GraphQLStatusError):
    """Error raised for invalid pagination arguments."""

    msg = "Invalid pagination arguments."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.INVALID_PAGINATION_ARGUMENTS


class GraphQLPermissionError(GraphQLStatusError):
    """Error raised when a permission check fails."""

    msg = "Permission denied."  # Users should add their own message.
    status = HTTPStatus.FORBIDDEN
    code = UndineErrorCodes.PERMISSION_DENIED


class GraphQLPersistedDocumentNotFoundError(GraphQLStatusError):
    """Error raised when a persisted document matching some document id does not exist."""

    msg = "Persisted document {document_id!r} not found."
    status = HTTPStatus.NOT_FOUND
    code = UndineErrorCodes.PERSISTED_DOCUMENT_NOT_FOUND


class GraphQLPersistedDocumentsNotSupportedError(GraphQLStatusError):
    """Error raised when trying to execute a persisted document without the correct app installed."""

    msg = "Server does not support persisted documents."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.PERSISTED_DOCUMENTS_NOT_SUPPORTED


class GraphQLRelationNotNullableError(GraphQLStatusError):
    """Error raised when trying to update a relation to null, but the relation is not nullable."""

    msg = "Field '{model:dotpath}.{field_name}' is not nullable. Existing relation cannot be set to null."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.FIELD_NOT_NULLABLE


class GraphQLRequestDecodingError(GraphQLStatusError):
    """Error raised when a request content cannot be decoded to python data."""

    msg = "Could not decode request."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.REQUEST_DECODING_ERROR


class GraphQLRequestParseError(GraphQLStatusError):
    """Error raised when a request content cannot be parsed to the expected format."""

    msg = "Could not parse request."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.REQUEST_PARSE_ERROR


class GraphQLScalarConversionError(GraphQLStatusError):
    """Error raised when a value cannot be converted to a GraphQL type."""

    msg = "'{typename}' cannot represent value {value}: {error}"
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.SCALAR_CONVERSION_ERROR


class GraphQLScalarInvalidValueError(GraphQLStatusError):
    """Error raised when a scalar cannot parse or serialize a given value."""

    msg = "Value is not a valid {typename}"
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.SCALAR_INVALID_VALUE


class GraphQLScalarTypeNotSupportedError(GraphQLStatusError):
    """Error raised when a scalar does not support a given type."""

    msg = "Type '{input_type:dotpath}' is not supported"
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.SCALAR_TYPE_NOT_SUPPORTED


class GraphQLTooManyFiltersError(GraphQLStatusError):
    """Error raised when too many filters are used for a single `FilterSet`."""

    msg = "{name!r} received {filter_count} filters which is more than the maximum allowed of {max_count}."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.TOO_MANY_FILTERS


class GraphQLTooManyOrdersError(GraphQLStatusError):
    """Error raised when too many orders are used for a single `OrderSet`."""

    msg = "{name!r} received {filter_count} orders which is more than the maximum allowed of {max_count}."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.TOO_MANY_ORDERS


class GraphQLUnionResolveTypeInvalidValueError(GraphQLStatusError):
    """Error raised when a union resolver fails to resolve a type for an invalid value."""

    msg = "Union '{name}' doesn't support {value!r} of type '{value:type}'."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.UNION_RESOLVE_TYPE_INVALID_VALUE


class GraphQLUnionResolveTypeModelNotFoundError(GraphQLStatusError):
    """Error raised when a union resolver fails to resolve a type for a given model."""

    msg = "Union '{name}' doesn't contain a type for model '{model:dotpath}'."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.UNION_RESOLVE_TYPE_MODEL_NOT_FOUND


class GraphQLUnexpectedError(GraphQLStatusError):
    """Error raised when an unexpected error occurs."""

    msg = "Unexpected error in GraphQL execution"
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    code = UndineErrorCodes.UNEXPECTED_ERROR


class GraphQLUnexpectedCalculationArgumentError(GraphQLStatusError):
    """Error raised if a calculation argument is unexpected."""

    msg = "Unexpected calculation arguments for field '{name}': {kwargs}."
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.MISSING_CALCULATION_ARGUMENT


class GraphQLUnsupportedContentTypeError(GraphQLStatusError):
    """Error raised when a request is made with an unsupported content type."""

    msg = "'{content_type}' is not a supported content type."
    status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    code = UndineErrorCodes.UNSUPPORTED_CONTENT_TYPE


class GraphQLValidationError(GraphQLStatusError):
    """Error meant to be raised for validation errors during mutations."""

    msg = "Validation error."  # Users should add their own message.
    status = HTTPStatus.BAD_REQUEST
    code = UndineErrorCodes.VALIDATION_ERROR
