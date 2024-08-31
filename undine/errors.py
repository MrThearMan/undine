from __future__ import annotations

from string import Formatter
from typing import Any, ClassVar

from graphql import GraphQLError, ValueNode, print_ast
from graphql.pyutils import inspect

__all__ = [
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
    "SchemaNameValidationError",
    "TypeDispatcherError",
    "TypeRegistryDuplicateError",
    "TypeRegistryMissingTypeError",
    "UndineError",
]


class ErrorMessageFormatter(Formatter):
    """Formatter for error strings."""

    def format_field(self, value: Any, format_spec: str) -> str:
        from undine.utils.text import comma_sep_str, dotpath

        if format_spec == "dotpath":
            return dotpath(value)
        if format_spec == "module":
            return value.__module__
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
    Error raised if provided model for `ModelGQLFilter` or `ModelGQLOrdering`
    doesn't match model of the given `ModelGQLType`.
    """

    msg = "'{cls}' model '{bad_model:dotpath}' does not match '{type}' model'{expected_model:dotpath}'."


class MissingFunctionAnnotationsError(UndineError):
    """Error raised if a function is missing type annotations for its parameters."""

    msg = "Missing type hints for parameters {missing:comma_sep_or} in function '{func:dotpath}'."


class MissingFunctionReturnTypeError(UndineError):
    """Error raised if a function does not contain a parameter to parse type from."""

    msg = "Missing type hint for return value in function '{func:dotpath}'."


class MissingModelError(UndineError):
    """Error raised if no model is provided to `ModelGQLType`, `ModelGQLFilter`, or `ModelGQLOrdering`."""

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


class TypeDispatcherError(UndineError):
    """Error raised for `TypeDispatcher` errors."""


class TypeRegistryDuplicateError(UndineError):
    """Error raised if trying to register a ModelGQLType for the same model twice."""

    msg = (
        "A 'ModelGQLType' for model '{model:dotpath}' "
        "has already been registered: '{graphql_type:dotpath}'. "
        "Use a proxy model or disable registration with "
        "`class MyType(ModelGQLType, model=MyModel, register=False)`. "
        "Note that the registered 'ModelGQLType' will be used when creating "
        "resolvers for related fields automatically."
    )


class TypeRegistryMissingTypeError(UndineError):
    """Error raised when a ModelGQLType for a model is not registered in the TypeRegistry."""

    msg = (
        "A 'ModelGQLType' for model '{model:dotpath}' has not been registered. "
        "Make sure one has been created and registered with "
        "`class MyType(ModelGQLType, model=MyModel, register=True)`. "
        "(by default, registration is enabled). For ModelGQLMutation, you can also "
        "provide the output type with the `output_type` keyword argument."
    )


# GraphQL Errors


class GraphQLStatusError(GraphQLError):
    def __init__(self, message: str, *, status: int, code: str, **kwargs: Any) -> None:
        extensions = kwargs.setdefault("extensions", {})
        extensions["status_code"] = status
        if code is not None:
            extensions["error_code"] = code
        super().__init__(message, **kwargs)


class GraphQLConversionError(GraphQLError):
    def __init__(self, name: str, value: Any, extra: str = "", **kwargs: Any) -> None:
        if isinstance(value, ValueNode):
            kwargs["nodes"] = value
            kwargs["message"] = f"{name} cannot represent value {print_ast(value)}"
        else:
            kwargs["message"] = f"{name} cannot represent value {inspect(value)}"

        if extra:
            kwargs["message"] += f": {extra}"

        super().__init__(**kwargs)
