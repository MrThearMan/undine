from __future__ import annotations

from abc import ABC, abstractmethod
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Unpack

from graphql import DirectiveLocation, GraphQLArgument, Undefined

from undine.converters import convert_to_graphql_type
from undine.dataclasses import TypeRef
from undine.exceptions import (
    GraphQLMissingCalculationArgumentError,
    GraphQLUnexpectedCalculationArgumentError,
    MissingCalculationReturnTypeError,
)
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.typing import T_co
from undine.utils.graphql.utils import check_directives
from undine.utils.reflection import get_members
from undine.utils.text import dotpath, to_schema_name

if TYPE_CHECKING:
    from graphql import GraphQLInputType

    from undine.directives import Directive
    from undine.typing import CalculationArgumentParams, DefaultValueType, DjangoExpression, GQLInfo, TypeHint

__all__ = [
    "Calculation",
    "CalculationArgument",
]


class Calculation(Generic[T_co], ABC):
    """
    An object that wraps logic for calculating a field's value based on defined input arguments.

    >>> class ExampleCalculation(Calculation[int]):
    ...     value = CalculationArgument(int)
    ...
    ...     def __call__(self, info: GQLInfo) -> DjangoExpression:
    ...         return Value(self.value)
    >>>
    >>> class TaskType(QueryType[Task]): ...
    >>>     example = Field(ExampleCalculation)
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `CalculationArgument` names.

    # Set in '__init_subclass__'
    __returns__: ClassVar[TypeHint]
    __arguments__: ClassVar[dict[str, CalculationArgument]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    @abstractmethod
    def __call__(self, info: GQLInfo) -> DjangoExpression:
        """Calculate the value of the Field. Return an expression that can be annotated to a queryset."""

    def __class_getitem__(cls, returns: TypeHint) -> type[Calculation[TypeHint]]:
        cls.__returns__ = returns
        return cls  # type: ignore[return-value]

    def __init_subclass__(cls) -> None:
        try:
            cls.__returns__ = Calculation.__returns__
            del Calculation.__returns__
        except AttributeError as error:
            raise MissingCalculationReturnTypeError(name=cls.__name__) from error

        cls.__arguments__ = get_members(cls, CalculationArgument)
        cls.__attribute_docstrings__ = parse_class_attribute_docstrings(cls)

        for name, arg in cls.__arguments__.items():
            arg.__connect__(cls, name)

    def __init__(self, __field_name__: str, /, **kwargs: Any) -> None:
        parameters: dict[str, Any] = {}

        for arg in self.__arguments__.values():
            value = kwargs.pop(arg.name, arg.default_value)
            if value is Undefined:
                raise GraphQLMissingCalculationArgumentError(arg=arg.name, name=__field_name__)

            parameters[arg.name] = value

        if kwargs:
            raise GraphQLUnexpectedCalculationArgumentError(name=__field_name__, kwargs=kwargs)

        self.__field_name__: str = __field_name__
        self.__parameters__: MappingProxyType[str, Any] = MappingProxyType(parameters)


class CalculationArgument:
    """Defines an input argument for a `Calculation`."""

    def __init__(self, ref: TypeHint, **kwargs: Unpack[CalculationArgumentParams]) -> None:
        """
        Create a new `CalculationArgument`.

        :param ref: The argument reference to use for the `CalculationArgument`.
        :param default_value: The default value for the `CalculationArgument`.
        :param description: Description for the `CalculationArgument`.
        :param deprecation_reason: If the `CalculationArgument` is deprecated, describes the reason for deprecation.
        :param schema_name: Actual name in the GraphQL schema. Only needed if argument name is a python keyword.
        :param directives: GraphQL directives for the `CalculationArgument`.
        :param extensions: GraphQL extensions for the `CalculationArgument`.
        """
        self.ref = ref

        self.default_value: DefaultValueType = kwargs.get("default_value", Undefined)
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")  # type: ignore[assignment]
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])  # type: ignore[assignment]
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})  # type: ignore[assignment]

        check_directives(self.directives, location=DirectiveLocation.ARGUMENT_DEFINITION)
        self.extensions[undine_settings.CALCULATION_ARGUMENT_EXTENSIONS_KEY] = self

    def __connect__(self, calculation: type[Calculation], name: str) -> None:
        self.calculation = calculation
        self.name = name
        self.schema_name = self.schema_name or to_schema_name(name)

        if self.description is Undefined:
            self.description = self.calculation.__attribute_docstrings__.get(name)

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref!r})>"

    def __str__(self) -> str:
        arg = self.as_graphql_argument()
        return undine_settings.SDL_PRINTER.print_field_argument(self.schema_name, arg, indent=False)

    def __get__(self, instance: Calculation | None, cls: type[Calculation]) -> Any:
        if instance is None:
            return self
        return instance.__parameters__[self.name]

    def as_graphql_argument(self) -> GraphQLArgument:
        return GraphQLArgument(
            type_=self.get_field_type(),
            default_value=self.default_value,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            out_name=self.name,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLInputType:
        return convert_to_graphql_type(TypeRef(self.ref), is_input=True)  # type: ignore[return-value]
