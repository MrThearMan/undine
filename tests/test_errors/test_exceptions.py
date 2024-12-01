from example_project.app.models import Project, Task
from undine import Entrypoint
from undine.errors.exceptions import (
    ErrorMessageFormatter,
    FunctionDispatcherError,
    FunctionSignatureParsingError,
    GraphQLBadInputDataError,
    GraphQLBadOrderDataError,
    GraphQLBulkMutationForwardRelationError,
    GraphQLBulkMutationGenericRelationsError,
    GraphQLBulkMutationManyRelatedError,
    GraphQLBulkMutationRelatedObjectNotFoundError,
    GraphQLBulkMutationReverseRelationError,
    GraphQLCantCreateEnumError,
    GraphQLConversionError,
    GraphQLDecodeError,
    GraphQLDuplicateTypeError,
    GraphQLEmptyQueryError,
    GraphQLFileParsingError,
    GraphQLInvalidInputDataError,
    GraphQLInvalidOperationError,
    GraphQLMissingContentTypeError,
    GraphQLMissingFileMapError,
    GraphQLMissingLookupFieldError,
    GraphQLMissingOperationsError,
    GraphQLModelConstaintViolationError,
    GraphQLModelNotFoundError,
    GraphQLMultipleObjectsFoundError,
    GraphQLPermissionDeniedError,
    GraphQLUnsupportedContentTypeError,
    InvalidParserError,
    MismatchingModelError,
    MissingEntrypointRefError,
    MissingFunctionAnnotationsError,
    MissingFunctionReturnTypeError,
    MissingModelError,
    ModelFieldDoesNotExistError,
    ModelFieldNotARelationError,
    NoFunctionParametersError,
    OptimizerError,
    PaginationArgumentValidationError,
    RegistryDuplicateError,
    RegistryMissingTypeError,
    SchemaNameValidationError,
)

# Testing error message formatter


formatter = ErrorMessageFormatter()


def test_error_formatter__dotpath():
    value = formatter.format_field(Entrypoint, format_spec="dotpath")
    assert value == "undine.schema.Entrypoint"


def test_error_formatter__module():
    value = formatter.format_field(Entrypoint, format_spec="module")
    assert value == "undine.schema"


def test_error_formatter__name():
    value = formatter.format_field(Entrypoint, format_spec="name")
    assert value == "Entrypoint"


def test_error_formatter__qualname():
    value = formatter.format_field(Entrypoint, format_spec="qualname")
    assert value == "Entrypoint"


def test_error_formatter__comma_sep_or():
    value = formatter.format_field(["foo", "bar", "baz"], format_spec="comma_sep_or")
    assert value == "'foo', 'bar' or 'baz'"


def test_error_formatter__comma_sep_and():
    value = formatter.format_field(["foo", "bar", "baz"], format_spec="comma_sep_and")
    assert value == "'foo', 'bar' and 'baz'"


# Tesing exception messages


def my_func() -> None: ...


class MyClass: ...


# Undine Errors


def test_error__function_signature_parsing_error():
    error = FunctionSignatureParsingError(name="foo", func=my_func)

    assert error.args[0] == (
        "Type 'foo' is not defined in module 'tests.test_errors.test_exceptions'. "
        "Check if it's inside a `if TYPE_CHECKING` block or another class/function. "
        "The type needs to be available at the runtime so that the signature of "
        "'my_func' can be inspected."
    )


def test_error__invalid_parser_error():
    error = InvalidParserError(cls=MyClass)

    assert error.args[0] == (
        "'tests.test_errors.test_exceptions.MyClass' does not implement 'DocstringParserProtocol'."
    )


def test_error__mismatching_model_error():
    error = MismatchingModelError(cls="foo", given_model=Task, type="bar", expected_model=Project)

    assert error.args[0] == (
        "'foo' model 'example_project.app.models.Task' does not "
        "match 'bar' model 'example_project.app.models.Project'."
    )


def test_error__missing_entrypoint_ref_error():
    error = MissingEntrypointRefError(name="foo", cls="bar")

    assert error.args[0] == "Entrypoint 'foo' in class 'bar' must have a reference."


def test_error__missing_function_annotations_error():
    error = MissingFunctionAnnotationsError(missing=["foo", "bar"], func=my_func)

    assert error.args[0] == (
        "Missing type hints for parameters 'foo' and 'bar' in function 'tests.test_errors.test_exceptions.my_func'."
    )


def test_error__missing_function_return_type_error():
    error = MissingFunctionReturnTypeError(func=my_func)

    assert error.args[0] == (
        "Missing type hint for return value in function 'tests.test_errors.test_exceptions.my_func'."
    )


def test_error__missing_model_error():
    error = MissingModelError(name="Foo", cls="MyClass")

    assert error.args[0] == (
        "'Foo' is missing `model` keyword argument in its class definition: `class Foo(MyClass, model=MyModel)`."
    )


def test_error__model_field_does_not_exist_error():
    error = ModelFieldDoesNotExistError(field="foo", model=Task)

    assert error.args[0] == "Field 'foo' does not exist in model 'example_project.app.models.Task'."


def test_error__model_field_not_arelation_error():
    error = ModelFieldNotARelationError(field="foo", model=Task)

    assert error.args[0] == "Field 'foo' is not a relation in model 'example_project.app.models.Task'."


def test_error__no_function_parameters_error():
    error = NoFunctionParametersError(func=my_func)

    assert error.args[0] == "Function 'tests.test_errors.test_exceptions.my_func' must have at least one argument."


def test_error__optimizer_error():
    error = OptimizerError("Error optimizing")

    assert error.args[0] == "Error optimizing"


def test_error__pagination_argument_validation_error():
    error = PaginationArgumentValidationError("Error with arguments")

    assert error.args[0] == "Error with arguments"


def test_error__schema_name_validation_error():
    error = SchemaNameValidationError(name="123")

    assert error.args[0] == (
        "'123' is not not an allowed name. "
        "Names must be in 'snake_case', all lower case, and cannot begin or end with an underscore. "
        "Also, any underscores must be followed by a letter due ambiguousness when converting "
        "values like 'the_1st' vs 'the1st' to 'camelCase' and then back to 'snake_case'."
    )


def test_error__function_dispatcher_error():
    error = FunctionDispatcherError("Error with dispatcher")

    assert error.args[0] == "Error with dispatcher"


def test_error__registry_duplicate_error():
    error = RegistryDuplicateError(registry_name="foo", key="bar", value="baz")

    assert error.args[0] == "'foo' alrady contains a value for 'bar': 'baz'"


def test_error__registry_missing_type_error():
    error = RegistryMissingTypeError(registry_name="foo", key="bar")

    assert error.args[0] == "'foo' doesn't contain an entry for 'bar'"


# GraphQL Errors


def test_error__graphql_cant_create_enum_error():
    error = GraphQLCantCreateEnumError(name="foo")

    assert error.message == "Cannot create GraphQL Enum 'foo' with zero values."
    assert error.extensions == {"error_code": "GRAPHQL_CANT_CREATE_ENUM", "status_code": 400}


def test_error__graphql_bulk_mutation_reverse_relation_error():
    error = GraphQLBulkMutationReverseRelationError(name="foo", model=Task)

    assert error.message == (
        "'foo' is a reverse relation of model 'example_project.app.models.Task'. "
        "Bulk mutations do not support reverse relations."
    )
    assert error.extensions == {"error_code": "INVALID_INPUT_DATA", "status_code": 400}


def test_error__graphql_bulk_mutation_many_related_error():
    error = GraphQLBulkMutationManyRelatedError(name="foo", model=Task)

    assert error.message == (
        "'foo' is a many-to-many related field on 'example_project.app.models.Task'. "
        "Bulk mutations do not support many-to-many relations."
    )
    assert error.extensions == {"error_code": "INVALID_INPUT_DATA", "status_code": 400}


def test_error__graphql_bulk_mutation_generic_relations_error():
    error = GraphQLBulkMutationGenericRelationsError(name="foo", model=Task)

    assert error.message == (
        "'foo' is a generic relation on 'example_project.app.models.Task'. "
        "Bulk mutations do not support generic relations."
    )
    assert error.extensions == {"error_code": "INVALID_INPUT_DATA", "status_code": 400}


def test_error__graphql_bulk_mutation_forward_relation_error():
    error = GraphQLBulkMutationForwardRelationError(name="foo", model=Task)

    assert error.message == (
        "Bulk mutations only work when setting existing forward one-to-one and many-to-one related objects. "
        "Creating new related objects is not supported. Please modify the MutationType by setting "
        "`foo = Input(Task.foo)` in the class definition."
    )
    assert error.extensions == {"error_code": "INVALID_INPUT_DATA", "status_code": 400}


def test_error__graphql_bulk_mutation_related_object_not_found_error():
    error = GraphQLBulkMutationRelatedObjectNotFoundError(name="foo", model=Task, value=1)

    assert error.message == (
        "Tried to link related field 'foo' to related model 'example_project.app.models.Task' "
        "with the primary key 1 but no such object was found."
    )
    assert error.extensions == {"error_code": "INVALID_INPUT_DATA", "status_code": 404}


def test_error__graphql_conversion_error():
    error = GraphQLConversionError(typename="foo", value=1, error="bar")

    assert error.message == "'foo' cannot represent value 1: bar"
    assert error.extensions == {"error_code": "GRAPHQL_CONVERSION_ERROR", "status_code": 400}


def test_error__graphql_decode_error():
    error = GraphQLDecodeError("Error decoding")

    assert error.message == "Error decoding"
    assert error.extensions == {"error_code": "DECODING_ERROR", "status_code": 400}


def test_error__graphql_duplicate_type_error():
    error = GraphQLDuplicateTypeError(name="foo", type_existing=Project, type_new=Task)

    assert error.message == (
        "GraphQL schema already has a known type with the name 'foo': "
        "'example_project.app.models.Project'. Cannot add a new type 'example_project.app.models.Task'."
    )
    assert error.extensions == {"error_code": "GRAPHQL_DUPLICATE_ENUM", "status_code": 400}


def test_error__graphql_empty_query_error():
    error = GraphQLEmptyQueryError()

    assert error.message == "Requests must contain a `query` string describing the graphql document."
    assert error.extensions == {"error_code": "EMPTY_QUERY", "status_code": 400}


def test_error__graphql_file_parsing_error():
    error = GraphQLFileParsingError("Error parsing query")

    assert error.message == "Error parsing query"
    assert error.extensions == {"error_code": "FILE_NOT_FOUND", "status_code": 400}


def test_error__graphql_invalid_input_data_error():
    error = GraphQLInvalidInputDataError(field_name="foo", data=[1, 2, 3])

    assert error.message == "Invalid input data for field 'foo': [1, 2, 3]"
    assert error.extensions == {"error_code": "INVALID_INPUT_DATA", "status_code": 400}


def test_error__graphql_invalid_operation_error():
    error = GraphQLInvalidOperationError(field_name="foo", model=Task, value="bar")

    assert error.message == "Only query operations are allowed on GET requests."
    assert error.extensions == {"error_code": "INVALID_OPERATION_FOR_METHOD", "status_code": 405}


def test_error__graphql_bad_input_data_error():
    error = GraphQLBadInputDataError(field_name="foo", mutation_type=MyClass)

    assert error.message == (
        "Input data contains data for field 'foo' but MutationType "
        "'tests.test_errors.test_exceptions.MyClass' doesn't have an input with that name."
    )
    assert error.extensions == {"error_code": "INVALID_INPUT_DATA", "status_code": 400}


def test_error__graphql_bad_order_data_error():
    error = GraphQLBadOrderDataError(enum_value="foo", orderset=MyClass)

    assert error.message == (
        "Order data contains ordering value 'foo' but OrderSet "
        "'tests.test_errors.test_exceptions.MyClass' doesn't have support an order with that name."
    )
    assert error.extensions == {"error_code": "INVALID_ORDER_DATA", "status_code": 400}


def test_error__graphql_missing_content_type_error():
    error = GraphQLMissingContentTypeError()

    assert error.message == "Must provide a 'Content-Type' header."
    assert error.extensions == {"error_code": "CONTENT_TYPE_MISSING", "status_code": 415}


def test_error__graphql_missing_file_map_error():
    error = GraphQLMissingFileMapError()

    assert error.message == "File upload must contain an `map` value."
    assert error.extensions == {"error_code": "MISSING_FILE_MAP", "status_code": 400}


def test_error__graphql_missing_lookup_field_error():
    error = GraphQLMissingLookupFieldError(key="foo", model=Task)

    assert error.message == (
        "Input data is missing value for the mutation lookup field 'foo'. "
        "Cannot fetch 'example_project.app.models.Task' object for mutation."
    )
    assert error.extensions == {"error_code": "LOOKUP_VALUE_MISSING", "status_code": 400}


def test_error__graphql_missing_operations_error():
    error = GraphQLMissingOperationsError()

    assert error.message == "File upload must contain an `operations` value."
    assert error.extensions == {"error_code": "MISSING_OPERATIONS", "status_code": 400}


def test_error__graphql_model_constaint_violation_error():
    error = GraphQLModelConstaintViolationError("Violation")

    assert error.message == "Violation"
    assert error.extensions == {"error_code": "MODEL_CONSTRAINT_VIOLATION", "status_code": 400}


def test_error__graphql_model_not_found_error():
    error = GraphQLModelNotFoundError(key="foo", value="bar", model=Task)

    assert error.message == "Lookup `foo='bar'` on model 'example_project.app.models.Task' did not match any row."
    assert error.extensions == {"error_code": "MODEL_NOT_FOUND", "status_code": 404}


def test_error__graphql_multiple_objects_found_error():
    error = GraphQLMultipleObjectsFoundError(key="foo", value="bar", model=Task)

    assert error.message == "Lookup `foo='bar'` on model 'example_project.app.models.Task' matched more than one row."
    assert error.extensions == {"error_code": "MODEL_MULTIPLE_OBJECTS", "status_code": 500}


def test_error__graphql_permission_denied_error():
    error = GraphQLPermissionDeniedError()

    assert error.message == "Permission denied."
    assert error.extensions == {"error_code": "PERMISSION_DENIED", "status_code": 403}


def test_error__graphql_unsupported_content_type_error():
    error = GraphQLUnsupportedContentTypeError(content_type="application/example")

    assert error.message == "'application/example' is not a supported content type."
    assert error.extensions == {"error_code": "UNSUPPORTED_CONTENT_TYPE", "status_code": 415}
