from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any, Generic, NoReturn, TypeVar

from django.core.exceptions import ValidationError
from graphql import DirectiveLocation, GraphQLScalarType
from graphql.pyutils import inspect

from undine.directives import Directive
from undine.exceptions import GraphQLScalarConversionError, GraphQLScalarTypeNotSupportedError
from undine.settings import undine_settings
from undine.typing import DispatchProtocol, T
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.graphql.type_registry import get_or_create_graphql_scalar
from undine.utils.graphql.utils import check_directives
from undine.utils.text import dotpath

__all__ = [
    "ScalarType",
]

TParse = TypeVar("TParse")
TSerialize = TypeVar("TSerialize")


class ScalarType(Generic[TParse, TSerialize]):
    """
    Create a new scalar for the GraphQL Schema.

    >>> my_scalar = ScalarType(name="MyScalar")
    >>> my_scalar.as_graphql_scalar()
    <GraphQLScalarType "MyScalar">
    """

    def __init__(
        self,
        name: str,
        description: str | None = None,
        specified_by_url: str | None = None,
        directives: Iterable[Directive] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        Create a new `ScalarType`.

        :param name: The name of the 'ScalarType'.
        :param description: Description of the 'ScalarType'.
        :param specified_by_url: URL to the specification of the 'ScalarType'.
        :param directives: GraphQL directives for the 'ScalarType'.
        :param extensions: GraphQL extensions for the 'ScalarType'.
        """
        self.name = name
        self.description = description
        self.specified_by_url = specified_by_url
        self.directives = directives or []
        self.extensions = extensions or {}

        check_directives(self.directives, location=DirectiveLocation.SCALAR)
        self.extensions[undine_settings.SCALAR_EXTENSIONS_KEY] = self

        error_wrapper = handle_scalar_errors(name)
        self.parse: FunctionDispatcher[TParse] = FunctionDispatcher(wrapper=error_wrapper)
        self.serialize: FunctionDispatcher[TSerialize] = FunctionDispatcher(wrapper=error_wrapper)

        @self.serialize.register
        @self.parse.register
        def _(value: Any) -> NoReturn:
            raise GraphQLScalarTypeNotSupportedError(input_type=type(value))

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(name={self.name!r})>"

    def __str__(self) -> str:
        return undine_settings.SDL_PRINTER.print_scalar_type(self.as_graphql_scalar())

    def as_graphql_scalar(self) -> GraphQLScalarType:
        return get_or_create_graphql_scalar(
            name=self.name,
            description=self.description,
            serialize=self.serialize,
            parse_value=self.parse,
            specified_by_url=self.specified_by_url,
            extensions=self.extensions,
        )


def handle_scalar_errors(typename: str) -> Callable[[DispatchProtocol[T]], DispatchProtocol[T]]:
    """Catch errors raised by the scalar parsers and serializers and reraise them as GraphQLErrors."""

    def decorator(func: DispatchProtocol[T]) -> DispatchProtocol[T]:
        @wraps(func)
        def wrapper(key: Any, **kwargs: Any) -> T:
            try:
                return func(key)
            except GraphQLScalarConversionError:
                raise
            except ValidationError as err:
                msg = str(err.message % err.params) if err.params else str(err.message)
                raise GraphQLScalarConversionError(typename=typename, value=inspect(key), error=msg) from err
            except Exception as err:
                raise GraphQLScalarConversionError(typename=typename, value=inspect(key), error=str(err)) from err

        return wrapper  # type: ignore[return-value]

    return decorator
