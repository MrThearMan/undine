from __future__ import annotations

from typing import Any, NamedTuple

import pytest
from django.db.models import Q
from django.db.models.fields import CharField
from graphql import DirectiveLocation, GraphQLError

from example_project.app.models import Project, Task
from tests.helpers import parametrize_helper
from undine import Entrypoint
from undine.exceptions import (
    DirectiveLocationError,
    EmptyFilterResult,
    ErrorMessageFormatter,
    ExpressionMultipleOutputFieldError,
    ExpressionNoOutputFieldError,
    FunctionDispatcherImplementationNotFoundError,
    FunctionDispatcherImproperLiteralError,
    FunctionDispatcherNoArgumentAnnotationError,
    FunctionDispatcherNoArgumentsError,
    FunctionDispatcherNonRuntimeProtocolError,
    FunctionDispatcherRegistrationError,
    FunctionDispatcherUnionTypeError,
    FunctionDispatcherUnknownArgumentError,
    FunctionSignatureParsingError,
    GraphQLAsyncNotSupportedError,
    GraphQLDuplicateTypeError,
    GraphQLErrorGroup,
    GraphQLFileNotFoundError,
    GraphQLFilePlacingError,
    GraphQLGetRequestMultipleOperationsNoOperationNameError,
    GraphQLGetRequestNonQueryOperationError,
    GraphQLGetRequestNoOperationError,
    GraphQLGetRequestOperationNotFoundError,
    GraphQLInvalidInputDataError,
    GraphQLInvalidOrderDataError,
    GraphQLMissingCalculationArgumentError,
    GraphQLMissingContentTypeError,
    GraphQLMissingDocumentIDError,
    GraphQLMissingFileMapError,
    GraphQLMissingInstancesToDeleteError,
    GraphQLMissingLookupFieldError,
    GraphQLMissingOperationsError,
    GraphQLMissingQueryAndDocumentIDError,
    GraphQLMissingQueryError,
    GraphQLModelConstraintViolationError,
    GraphQLModelNotFoundError,
    GraphQLModelsNotFoundError,
    GraphQLMutationInputNotFoundError,
    GraphQLMutationInstanceLimitError,
    GraphQLMutationTreeModelMismatchError,
    GraphQLNodeIDFieldTypeError,
    GraphQLNodeInterfaceMissingError,
    GraphQLNodeInvalidGlobalIDError,
    GraphQLNodeMissingIDFieldError,
    GraphQLNodeObjectTypeMissingError,
    GraphQLNodeQueryTypeMissingError,
    GraphQLNodeTypeNotObjectTypeError,
    GraphQLNoExecutionResultError,
    GraphQLOptimizerError,
    GraphQLPaginationArgumentValidationError,
    GraphQLPermissionError,
    GraphQLPersistedDocumentNotFoundError,
    GraphQLPersistedDocumentsNotSupportedError,
    GraphQLRelationNotNullableError,
    GraphQLRequestDecodingError,
    GraphQLRequestParseError,
    GraphQLScalarConversionError,
    GraphQLScalarInvalidValueError,
    GraphQLScalarTypeNotSupportedError,
    GraphQLStatusError,
    GraphQLTooManyFiltersError,
    GraphQLTooManyOrdersError,
    GraphQLUnexpectedCalculationArgumentError,
    GraphQLUnexpectedError,
    GraphQLUnionResolveTypeInvalidValueError,
    GraphQLUnionResolveTypeModelNotFoundError,
    GraphQLUnsupportedContentTypeError,
    GraphQLValidationError,
    InvalidDocstringParserError,
    InvalidEntrypointMutationTypeError,
    InvalidInputMutationTypeError,
    MismatchingModelError,
    MissingCalculationReturnTypeError,
    MissingDirectiveArgumentError,
    MissingDirectiveLocationsError,
    MissingEntrypointRefError,
    MissingFunctionAnnotationsError,
    MissingFunctionReturnTypeError,
    MissingModelGenericError,
    ModelFieldDoesNotExistError,
    ModelFieldNotARelationError,
    NoFunctionParametersError,
    RegistryDuplicateError,
    RegistryMissingTypeError,
    UndineError,
    UndineErrorGroup,
    UnexpectedDirectiveArgumentError,
)

# Testing error message formatter


formatter = ErrorMessageFormatter()


def test_error_formatter__dotpath() -> None:
    value = formatter.format_field(Entrypoint, format_spec="dotpath")
    assert value == "undine.entrypoint.Entrypoint"


def test_error_formatter__module() -> None:
    value = formatter.format_field(Entrypoint, format_spec="module")
    assert value == "undine.entrypoint"


def test_error_formatter__name() -> None:
    value = formatter.format_field(Entrypoint, format_spec="name")
    assert value == "Entrypoint"


def test_error_formatter__qualname() -> None:
    value = formatter.format_field(Entrypoint, format_spec="qualname")
    assert value == "Entrypoint"


def test_error_formatter__comma_sep_or() -> None:
    value = formatter.format_field(["foo", "bar", "baz"], format_spec="comma_sep_or")
    assert value == "'foo', 'bar' or 'baz'"


def test_error_formatter__comma_sep_and() -> None:
    value = formatter.format_field(["foo", "bar", "baz"], format_spec="comma_sep_and")
    assert value == "'foo', 'bar' and 'baz'"


# Testing exception messages


def my_func() -> None: ...


class MyClass: ...


class UndineErrorParams(NamedTuple):
    cls: type[UndineError]
    args: dict[str, Any]
    message: str


@pytest.mark.parametrize(
    **parametrize_helper({
        "DirectiveLocationError": UndineErrorParams(
            cls=DirectiveLocationError,
            args={"directive": "foo", "location": DirectiveLocation.OBJECT},
            message="Directive 'foo' is not allowed in 'OBJECT'",
        ),
        "EmptyFilterResult": UndineErrorParams(
            cls=EmptyFilterResult,
            args={},
            message="Filter result should be null.",
        ),
        "ExpressionMultipleOutputFieldError": UndineErrorParams(
            cls=ExpressionMultipleOutputFieldError,
            args={"expr": Q(), "output_fields": [CharField]},
            message=(
                "Could not determine an output field for expression <Q: (AND: )>. "
                "Got multiple possible output fields: "
                "[<class 'django.db.models.fields.CharField'>]."
            ),
        ),
        "ExpressionNoOutputFieldError": UndineErrorParams(
            cls=ExpressionNoOutputFieldError,
            args={"expr": Q()},
            message=(
                "Could not determine an output field for expression <Q: (AND: )>. "
                "No output field found from any source expressions."
            ),
        ),
        "FunctionSignatureParsingError": UndineErrorParams(
            cls=FunctionSignatureParsingError,
            args={"name": "foo", "func": my_func},
            message=(
                "Type 'foo' is not defined in module 'tests.test_exceptions'. "
                "Check if it's inside a `if TYPE_CHECKING` block or another class/function. "
                "The type needs to be available at the runtime so that "
                "the signature of 'my_func' can be inspected."
            ),
        ),
        "InvalidInputMutationTypeError": UndineErrorParams(
            cls=InvalidInputMutationTypeError,
            args={"ref": MyClass, "kind": "create"},
            message=(
                "MutationType 'tests.test_exceptions.MyClass' is a 'create' MutationType, "
                "but only 'related' MutationTypes can be used as Inputs on other MutationTypes."
            ),
        ),
        "InvalidDocstringParserError": UndineErrorParams(
            cls=InvalidDocstringParserError,
            args={"cls": MyClass},
            message="'tests.test_exceptions.MyClass' does not implement 'DocstringParserProtocol'.",
        ),
        "InvalidEntrypointMutationTypeError": UndineErrorParams(
            cls=InvalidEntrypointMutationTypeError,
            args={"ref": MyClass, "kind": "related"},
            message=(
                "MutationType 'tests.test_exceptions.MyClass' is a 'related' MutationType, "
                "but only 'create', 'update', 'delete', or 'custom' MutationTypes can be used in Entrypoints."
            ),
        ),
        "MismatchingModelError": UndineErrorParams(
            cls=MismatchingModelError,
            args={"name": "FilterSet", "given_model": Task, "target": "TaskType", "expected_model": Project},
            message=(
                "'FilterSet' model 'example_project.app.models.Task' "
                "does not match 'TaskType' model 'example_project.app.models.Project'."
            ),
        ),
        "MissingCalculationReturnTypeError": UndineErrorParams(
            cls=MissingCalculationReturnTypeError,
            args={"name": "Calc"},
            message=(
                "'Calc' must define the calculation return type using the Generic type argument: "
                "e.g. `class Calc(Calculation[int]):`"
            ),
        ),
        "MissingEntrypointRefError": UndineErrorParams(
            cls=MissingEntrypointRefError,
            args={"name": "foo", "cls": MyClass},
            message="Entrypoint 'foo' in class 'tests.test_exceptions.MyClass' must have a reference.",
        ),
        "MissingFunctionAnnotationsError": UndineErrorParams(
            cls=MissingFunctionAnnotationsError,
            args={"missing": ["foo", "bar"], "func": my_func},
            message="Missing type hints for parameters 'foo' and 'bar' in function 'tests.test_exceptions.my_func'.",
        ),
        "MissingFunctionReturnTypeError": UndineErrorParams(
            cls=MissingFunctionReturnTypeError,
            args={"func": my_func},
            message="Missing type hint for return value in function 'tests.test_exceptions.my_func'.",
        ),
        "MissingDirectiveArgumentError": UndineErrorParams(
            cls=MissingDirectiveArgumentError,
            args={"name": "foo", "directive": MyClass},
            message="Missing directive argument 'foo' for directive 'tests.test_exceptions.MyClass'.",
        ),
        "MissingDirectiveLocationsError": UndineErrorParams(
            cls=MissingDirectiveLocationsError,
            args={"name": "MyDirective"},
            message=(
                "'MyDirective' is missing `locations` keyword argument in its class definition: "
                "e.g. `class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION])`."
            ),
        ),
        "MissingModelGenericError": UndineErrorParams(
            cls=MissingModelGenericError,
            args={"name": "TaskType", "cls": "QueryType"},
            message="'TaskType' is missing its generic types: `class TaskType(QueryType[MyModel])`.",
        ),
        "ModelFieldDoesNotExistError": UndineErrorParams(
            cls=ModelFieldDoesNotExistError,
            args={"field": "foo", "model": Task},
            message="Field 'foo' does not exist in model 'example_project.app.models.Task'.",
        ),
        "ModelFieldNotARelationError": UndineErrorParams(
            cls=ModelFieldNotARelationError,
            args={"field": "foo", "model": Task},
            message="Field 'foo' is not a relation in model 'example_project.app.models.Task'.",
        ),
        "NoFunctionParametersError": UndineErrorParams(
            cls=NoFunctionParametersError,
            args={"func": my_func},
            message="Function 'tests.test_exceptions.my_func' must have at least one argument.",
        ),
        "FunctionDispatcherImplementationNotFoundError": UndineErrorParams(
            cls=FunctionDispatcherImplementationNotFoundError,
            args={"name": "foo", "key": 1, "cls": MyClass},
            message="'foo' doesn't contain an implementation for 1 (type: tests.test_exceptions.MyClass).",
        ),
        "FunctionDispatcherImproperLiteralError": UndineErrorParams(
            cls=FunctionDispatcherImproperLiteralError,
            args={"arg": "foo"},
            message="Literal argument must be a string, integer, bytes, boolean, enum, or None, got 'foo'.",
        ),
        "FunctionDispatcherNoArgumentAnnotationError": UndineErrorParams(
            cls=FunctionDispatcherNoArgumentAnnotationError,
            args={"func_name": "foo", "name": "bar"},
            message=(
                "Function 'foo' must have a type hint for its first argument so that it can be registered for 'bar'."
            ),
        ),
        "FunctionDispatcherNoArgumentsError": UndineErrorParams(
            cls=FunctionDispatcherNoArgumentsError,
            args={"func_name": "foo", "name": "bar"},
            message="Function 'foo' must have at least one argument so that it can be registered for 'bar'.",
        ),
        "FunctionDispatcherNonRuntimeProtocolError": UndineErrorParams(
            cls=FunctionDispatcherNonRuntimeProtocolError,
            args={"name": "MyProtocol"},
            message="Protocol 'MyProtocol' is not a runtime checkable protocol.",
        ),
        "FunctionDispatcherRegistrationError": UndineErrorParams(
            cls=FunctionDispatcherRegistrationError,
            args={"name": "foo", "value": 1},
            message="Can only register functions with 'foo'. Got 1.",
        ),
        "FunctionDispatcherUnionTypeError": UndineErrorParams(
            cls=FunctionDispatcherUnionTypeError,
            args={"args": [1, 2]},
            message="Union type must have a single non-null type argument, got [1, 2].",
        ),
        "FunctionDispatcherUnknownArgumentError": UndineErrorParams(
            cls=FunctionDispatcherUnknownArgumentError,
            args={"annotation": "foo"},
            message="Unknown argument: 'foo'",
        ),
        "RegistryDuplicateError": UndineErrorParams(
            cls=RegistryDuplicateError,
            args={"registry_name": "foo", "key": "bar", "value": "baz"},
            message="'foo' already contains a value for 'bar': 'baz'",
        ),
        "RegistryMissingTypeError": UndineErrorParams(
            cls=RegistryMissingTypeError,
            args={"registry_name": "foo", "key": "bar"},
            message="'foo' doesn't contain an entry for 'bar'",
        ),
        "UnexpectedDirectiveArgumentError": UndineErrorParams(
            cls=UnexpectedDirectiveArgumentError,
            args={"directive": MyClass, "kwargs": {"foo": "bar"}},
            message="Unexpected directive arguments for directive 'tests.test_exceptions.MyClass': {'foo': 'bar'}.",
        ),
    })
)
def test_undine_error(cls, args, message) -> None:
    error = cls(**args)
    assert error.args[0] == message


class GQLErrorParams(NamedTuple):
    cls: type[GraphQLStatusError]
    args: dict[str, Any]
    message: str
    extensions: dict[str, Any]


@pytest.mark.parametrize(
    **parametrize_helper({
        "GraphQLAsyncNotSupportedError": GQLErrorParams(
            cls=GraphQLAsyncNotSupportedError,
            args={},
            message="GraphQL execution failed to complete synchronously.",
            extensions={"error_code": "ASYNC_NOT_SUPPORTED", "status_code": 500},
        ),
        "GraphQLDuplicateTypeError": GQLErrorParams(
            cls=GraphQLDuplicateTypeError,
            args={"name": "foo", "type_existing": Project, "type_new": Task},
            message=(
                "GraphQL schema already has a known type with the name "
                "'foo': '<class 'example_project.app.models.Project'>'. "
                "Cannot add a new type '<class 'example_project.app.models.Task'>'."
            ),
            extensions={"error_code": "DUPLICATE_TYPE", "status_code": 400},
        ),
        "GraphQLFilePlacingError": GQLErrorParams(
            cls=GraphQLFilePlacingError,
            args={"value": {"map": {"foo": ["bar"]}}},
            message="Value '{'map': {'foo': ['bar']}}' in file map does not lead to a null value.",
            extensions={"error_code": "FILE_NOT_FOUND", "status_code": 400},
        ),
        "GraphQLFileNotFoundError": GQLErrorParams(
            cls=GraphQLFileNotFoundError,
            args={"key": "foo"},
            message="File for path 'foo' not found in request files.",
            extensions={"error_code": "FILE_NOT_FOUND", "status_code": 400},
        ),
        "GraphQLGetRequestMultipleOperationsNoOperationNameError": GQLErrorParams(
            cls=GraphQLGetRequestMultipleOperationsNoOperationNameError,
            args={},
            message="Must provide operation name if query contains multiple operations.",
            extensions={"error_code": "MISSING_OPERATION_NAME", "status_code": 405},
        ),
        "GraphQLGetRequestNonQueryOperationError": GQLErrorParams(
            cls=GraphQLGetRequestNonQueryOperationError,
            args={},
            message="Only query operations are allowed on GET requests.",
            extensions={"error_code": "INVALID_OPERATION_FOR_METHOD", "status_code": 405},
        ),
        "GraphQLGetRequestNoOperationError": GQLErrorParams(
            cls=GraphQLGetRequestNoOperationError,
            args={},
            message="Must provide an operation.",
            extensions={"error_code": "NO_OPERATION", "status_code": 405},
        ),
        "GraphQLGetRequestOperationNotFoundError": GQLErrorParams(
            cls=GraphQLGetRequestOperationNotFoundError,
            args={"operation_name": "foo"},
            message="Unknown operation named 'foo'.",
            extensions={"error_code": "OPERATION_NOT_FOUND", "status_code": 405},
        ),
        "GraphQLInvalidInputDataError": GQLErrorParams(
            cls=GraphQLInvalidInputDataError,
            args={"field_name": "foo", "data": {"bar": "baz"}, "error": "fizz"},
            message="Invalid input data for field 'foo': {'bar': 'baz'}",
            extensions={"error_code": "INVALID_INPUT_DATA", "status_code": 400},
        ),
        "GraphQLInvalidOrderDataError": GQLErrorParams(
            cls=GraphQLInvalidOrderDataError,
            args={"enum_value": "foo", "orderset": MyClass},
            message=(
                "Order data contains ordering value 'foo' but OrderSet "
                "'tests.test_exceptions.MyClass' doesn't have support an order with that name."
            ),
            extensions={"error_code": "INVALID_ORDER_DATA", "status_code": 400},
        ),
        "GraphQLMissingCalculationArgumentError": GQLErrorParams(
            cls=GraphQLMissingCalculationArgumentError,
            args={"arg": "foo", "name": "bar"},
            message="Missing calculation argument 'foo' for calculation 'bar'.",
            extensions={"error_code": "MISSING_CALCULATION_ARGUMENT", "status_code": 400},
        ),
        "GraphQLMissingContentTypeError": GQLErrorParams(
            cls=GraphQLMissingContentTypeError,
            args={},
            message="Must provide a 'Content-Type' header.",
            extensions={"error_code": "CONTENT_TYPE_MISSING", "status_code": 415},
        ),
        "GraphQLMissingFileMapError": GQLErrorParams(
            cls=GraphQLMissingFileMapError,
            args={},
            message="File upload must contain an `map` value.",
            extensions={"error_code": "MISSING_FILE_MAP", "status_code": 400},
        ),
        "GraphQLMissingLookupFieldError": GQLErrorParams(
            cls=GraphQLMissingLookupFieldError,
            args={"key": "foo", "model": Task},
            message=(
                "Input data is missing value for the mutation lookup field 'foo'. "
                "Cannot fetch 'example_project.app.models.Task' object for mutation."
            ),
            extensions={"error_code": "LOOKUP_VALUE_MISSING", "status_code": 400},
        ),
        "GraphQLMissingOperationsError": GQLErrorParams(
            cls=GraphQLMissingOperationsError,
            args={},
            message="File upload must contain an `operations` value.",
            extensions={"error_code": "MISSING_OPERATIONS", "status_code": 400},
        ),
        "GraphQLMissingDocumentIDError": GQLErrorParams(
            cls=GraphQLMissingDocumentIDError,
            args={},
            message="Request data must contain a `documentId` string identifying a persisted document.",
            extensions={"error_code": "MISSING_GRAPHQL_DOCUMENT_PARAMETER", "status_code": 400},
        ),
        "GraphQLMissingQueryError": GQLErrorParams(
            cls=GraphQLMissingQueryError,
            args={},
            message="Request data must contain a `query` string describing the graphql document.",
            extensions={"error_code": "MISSING_GRAPHQL_QUERY_PARAMETER", "status_code": 400},
        ),
        "GraphQLMissingQueryAndDocumentIDError": GQLErrorParams(
            cls=GraphQLMissingQueryAndDocumentIDError,
            args={},
            message=(
                "Request data must contain either a `query` string describing the graphql document "
                "or a `documentId` string identifying a persisted document."
            ),
            extensions={"error_code": "MISSING_GRAPHQL_QUERY_AND_DOCUMENT_PARAMETERS", "status_code": 400},
        ),
        "GraphQLMissingInstancesToDeleteError": GQLErrorParams(
            cls=GraphQLMissingInstancesToDeleteError,
            args={"given": 1, "to_delete": 0},
            message="Expected 1 instances to delete, but found 0.",
            extensions={"error_code": "MISSING_INSTANCES_TO_DELETE", "status_code": 400},
        ),
        "GraphQLModelConstraintViolationError": GQLErrorParams(
            cls=GraphQLModelConstraintViolationError,
            args={"message": "Violation"},
            message="Violation",
            extensions={"error_code": "MODEL_CONSTRAINT_VIOLATION", "status_code": 400},
        ),
        "GraphQLModelNotFoundError": GQLErrorParams(
            cls=GraphQLModelNotFoundError,
            args={"pk": 1, "model": Task},
            message="Primary key 1 on model 'example_project.app.models.Task' did not match any row.",
            extensions={"error_code": "MODEL_NOT_FOUND", "status_code": 404},
        ),
        "GraphQLModelsNotFoundError": GQLErrorParams(
            cls=GraphQLModelsNotFoundError,
            args={"missing": [1, 2], "model": Task},
            message="Primary keys '1' and '2' on model 'example_project.app.models.Task' did not match any row.",
            extensions={"error_code": "MODEL_NOT_FOUND", "status_code": 404},
        ),
        "GraphQLMutationInputNotFoundError": GQLErrorParams(
            cls=GraphQLMutationInputNotFoundError,
            args={"field_name": "foo", "mutation_type": MyClass},
            message=(
                "Input data contains data for field 'foo' but MutationType "
                "'tests.test_exceptions.MyClass' doesn't have an input with that name."
            ),
            extensions={"error_code": "INVALID_INPUT_DATA", "status_code": 400},
        ),
        "GraphQLMutationInstanceLimitError": GQLErrorParams(
            cls=GraphQLMutationInstanceLimitError,
            args={"limit": 100},
            message="Cannot mutate more than 100 objects in a single mutation.",
            extensions={"error_code": "MUTATION_TOO_MANY_OBJECTS", "status_code": 400},
        ),
        "GraphQLMutationTreeModelMismatchError": GQLErrorParams(
            cls=GraphQLMutationTreeModelMismatchError,
            args={"model_1": Task, "model_2": Project},
            message=(
                "Cannot merge MutationNodes for different models: "
                "'example_project.app.models.Task' and 'example_project.app.models.Project'."
            ),
            extensions={"error_code": "MUTATION_TREE_MODEL_MISMATCH", "status_code": 400},
        ),
        "GraphQLNodeIDFieldTypeError": GQLErrorParams(
            cls=GraphQLNodeIDFieldTypeError,
            args={"typename": "TaskType"},
            message=(
                "The 'id' field of the object type 'TaskType' must be of type 'ID' to comply with the 'Node' interface."
            ),
            extensions={"error_code": "NODE_ID_NOT_GLOBAL_ID", "status_code": 400},
        ),
        "GraphQLNodeInterfaceMissingError": GQLErrorParams(
            cls=GraphQLNodeInterfaceMissingError,
            args={"typename": "TaskType"},
            message="Object type 'TaskType' must implement the 'Node' interface.",
            extensions={"error_code": "NODE_INTERFACE_MISSING", "status_code": 400},
        ),
        "GraphQLNodeInvalidGlobalIDError": GQLErrorParams(
            cls=GraphQLNodeInvalidGlobalIDError,
            args={"value": "foo"},
            message="'foo' is not a valid Global ID.",
            extensions={"error_code": "NODE_INVALID_GLOBAL_ID", "status_code": 400},
        ),
        "GraphQLNodeMissingIDFieldError": GQLErrorParams(
            cls=GraphQLNodeMissingIDFieldError,
            args={"typename": "TaskType"},
            message="The object type 'TaskType' doesn't have an 'id' field.",
            extensions={"error_code": "NODE_QUERY_TYPE_ID_FIELD_MISSING", "status_code": 400},
        ),
        "GraphQLNodeObjectTypeMissingError": GQLErrorParams(
            cls=GraphQLNodeObjectTypeMissingError,
            args={"typename": "TaskType"},
            message="Object type 'TaskType' does not exist in schema.",
            extensions={"error_code": "NODE_MISSING_OBJECT_TYPE", "status_code": 400},
        ),
        "GraphQLNodeQueryTypeMissingError": GQLErrorParams(
            cls=GraphQLNodeQueryTypeMissingError,
            args={"typename": "TaskType"},
            message="Cannot find undine QueryType from object type 'TaskType'.",
            extensions={"error_code": "NODE_QUERY_TYPE_MISSING", "status_code": 400},
        ),
        "GraphQLNodeTypeNotObjectTypeError": GQLErrorParams(
            cls=GraphQLNodeTypeNotObjectTypeError,
            args={"typename": "TaskType"},
            message="Node ID type 'TaskType' is not an object type.",
            extensions={"error_code": "NODE_TYPE_NOT_OBJECT_TYPE", "status_code": 400},
        ),
        "GraphQLNoExecutionResultError": GQLErrorParams(
            cls=GraphQLNoExecutionResultError,
            args={},
            message="No execution result after GraphQL operation.",
            extensions={"error_code": "NO_EXECUTION_RESULT", "status_code": 500},
        ),
        "GraphQLOptimizerError": GQLErrorParams(
            cls=GraphQLOptimizerError,
            args={},
            message="GraphQL optimization failed.",
            extensions={"error_code": "OPTIMIZER_ERROR", "status_code": 500},
        ),
        "GraphQLPaginationArgumentValidationError": GQLErrorParams(
            cls=GraphQLPaginationArgumentValidationError,
            args={},
            message="Invalid pagination arguments.",
            extensions={"error_code": "INVALID_PAGINATION_ARGUMENTS", "status_code": 400},
        ),
        "GraphQLPermissionError": GQLErrorParams(
            cls=GraphQLPermissionError,
            args={},
            message="Permission denied.",
            extensions={"error_code": "PERMISSION_DENIED", "status_code": 403},
        ),
        "GraphQLPersistedDocumentNotFoundError": GQLErrorParams(
            cls=GraphQLPersistedDocumentNotFoundError,
            args={"document_id": "foo"},
            message="Persisted document 'foo' not found.",
            extensions={"error_code": "PERSISTED_DOCUMENT_NOT_FOUND", "status_code": 404},
        ),
        "GraphQLPersistedDocumentsNotSupportedError": GQLErrorParams(
            cls=GraphQLPersistedDocumentsNotSupportedError,
            args={},
            message="Server does not support persisted documents.",
            extensions={"error_code": "PERSISTED_DOCUMENTS_NOT_SUPPORTED", "status_code": 400},
        ),
        "GraphQLRelationNotNullableError": GQLErrorParams(
            cls=GraphQLRelationNotNullableError,
            args={"model": Task, "field_name": "name"},
            message=(
                "Field 'example_project.app.models.Task.name' is not nullable. Existing relation cannot be set to null."
            ),
            extensions={"error_code": "FIELD_NOT_NULLABLE", "status_code": 400},
        ),
        "GraphQLRequestDecodingError": GQLErrorParams(
            cls=GraphQLRequestDecodingError,
            args={},
            message="Could not decode request.",
            extensions={"error_code": "REQUEST_DECODING_ERROR", "status_code": 400},
        ),
        "GraphQLRequestParseError": GQLErrorParams(
            cls=GraphQLRequestParseError,
            args={},
            message="Could not parse request.",
            extensions={"error_code": "REQUEST_PARSE_ERROR", "status_code": 400},
        ),
        "GraphQLScalarConversionError": GQLErrorParams(
            cls=GraphQLScalarConversionError,
            args={"typename": "foo", "value": 1, "error": "bar"},
            message="'foo' cannot represent value 1: bar",
            extensions={"error_code": "SCALAR_CONVERSION_ERROR", "status_code": 400},
        ),
        "GraphQLScalarInvalidValueError": GQLErrorParams(
            cls=GraphQLScalarInvalidValueError,
            args={"typename": "foo"},
            message="Value is not a valid foo",
            extensions={"error_code": "SCALAR_INVALID_VALUE", "status_code": 400},
        ),
        "GraphQLScalarTypeNotSupportedError": GQLErrorParams(
            cls=GraphQLScalarTypeNotSupportedError,
            args={"input_type": MyClass},
            message="Type 'tests.test_exceptions.MyClass' is not supported",
            extensions={"error_code": "SCALAR_TYPE_NOT_SUPPORTED", "status_code": 400},
        ),
        "GraphQLTooManyFiltersError": GQLErrorParams(
            cls=GraphQLTooManyFiltersError,
            args={"name": "foo", "filter_count": 100, "max_count": 50},
            message="'foo' received 100 filters which is more than the maximum allowed of 50.",
            extensions={"error_code": "TOO_MANY_FILTERS", "status_code": 400},
        ),
        "GraphQLTooManyOrdersError": GQLErrorParams(
            cls=GraphQLTooManyOrdersError,
            args={"name": "foo", "filter_count": 100, "max_count": 50},
            message="'foo' received 100 orders which is more than the maximum allowed of 50.",
            extensions={"error_code": "TOO_MANY_ORDERS", "status_code": 400},
        ),
        "GraphQLUnionResolveTypeInvalidValueError": GQLErrorParams(
            cls=GraphQLUnionResolveTypeInvalidValueError,
            args={"name": "foo", "value": "bar"},
            message="Union 'foo' doesn't support 'bar' of type 'str'.",
            extensions={"error_code": "UNION_RESOLVE_TYPE_INVALID_VALUE", "status_code": 400},
        ),
        "GraphQLUnionResolveTypeModelNotFoundError": GQLErrorParams(
            cls=GraphQLUnionResolveTypeModelNotFoundError,
            args={"name": "foo", "model": Task},
            message="Union 'foo' doesn't contain a type for model 'example_project.app.models.Task'.",
            extensions={"error_code": "UNION_RESOLVE_TYPE_MODEL_NOT_FOUND", "status_code": 400},
        ),
        "GraphQLUnexpectedError": GQLErrorParams(
            cls=GraphQLUnexpectedError,
            args={},
            message="Unexpected error in GraphQL execution",
            extensions={"error_code": "UNEXPECTED_ERROR", "status_code": 500},
        ),
        "GraphQLUnexpectedCalculationArgumentError": GQLErrorParams(
            cls=GraphQLUnexpectedCalculationArgumentError,
            args={"name": "foo", "kwargs": {"bar": "baz"}},
            message="Unexpected calculation arguments for field 'foo': {'bar': 'baz'}.",
            extensions={"error_code": "MISSING_CALCULATION_ARGUMENT", "status_code": 400},
        ),
        "GraphQLUnsupportedContentTypeError": GQLErrorParams(
            cls=GraphQLUnsupportedContentTypeError,
            args={"content_type": "application/example"},
            message="'application/example' is not a supported content type.",
            extensions={"error_code": "UNSUPPORTED_CONTENT_TYPE", "status_code": 415},
        ),
        "GraphQLValidationError": GQLErrorParams(
            cls=GraphQLValidationError,
            args={},
            message="Validation error.",
            extensions={"error_code": "VALIDATION_ERROR", "status_code": 400},
        ),
    })
)
def test_graphql_error(cls, args, message, extensions) -> None:
    error = cls(**args)
    assert error.message == message
    assert error.extensions == extensions


def test_undine_error_group() -> None:
    error_1 = ValueError("foo")
    error_2 = ValueError("bar")
    error_3 = ValueError("baz")

    group_1 = UndineErrorGroup(errors=[error_1, error_2])
    group_2 = UndineErrorGroup(errors=[group_1, error_3])

    assert list(group_1.flatten()) == [error_1, error_2]
    assert list(group_2.flatten()) == [error_1, error_2, error_3]


def test_graphql_error_group() -> None:
    error_1 = GraphQLError("foo")
    error_2 = GraphQLError("bar")
    error_3 = GraphQLError("baz")

    group_1 = GraphQLErrorGroup(errors=[error_1, error_2])
    group_2 = GraphQLErrorGroup(errors=[group_1, error_3])

    assert list(group_1.flatten()) == [error_1, error_2]
    assert list(group_2.flatten()) == [error_1, error_2, error_3]

    error_4 = GraphQLError("fizz", path=["buzz"])

    group_2.located_by(error_4)

    assert error_1.path == ["buzz"]
    assert error_2.path == ["buzz"]
    assert error_3.path == ["buzz"]
