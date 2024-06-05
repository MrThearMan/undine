from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Unpack

from graphql import DirectiveLocation, GraphQLArgument, Undefined

from undine.exceptions import (
    MissingDirectiveArgumentError,
    MissingDirectiveLocationsError,
    UnexpectedDirectiveArgumentError,
)
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_directive
from undine.utils.graphql.utils import check_directives
from undine.utils.reflection import get_members
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from graphql import GraphQLDirective, GraphQLInputType

    from undine.typing import DefaultValueType, DirectiveArgumentParams, DirectiveParams

__all__ = [
    "Directive",
    "DirectiveArgument",
]


class DirectiveMeta(type):
    """A metaclass that modifies how a `Directive` is created."""

    # Set in '__new__'
    __locations__: list[DirectiveLocation]
    __arguments__: dict[str, DirectiveArgument]
    __is_repeatable__: bool
    __schema_name__: str
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[DirectiveParams],
    ) -> DirectiveMeta:
        if _name == "Directive":  # Early return for the `Directive` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        locations = kwargs.get("locations", [])
        if locations is None:
            raise MissingDirectiveLocationsError(name=_name)

        directive = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `DirectiveArgument` names.
        directive.__locations__ = [DirectiveLocation(location) for location in locations]
        directive.__arguments__ = get_members(directive, DirectiveArgument)
        directive.__is_repeatable__ = kwargs.get("is_repeatable", False)
        directive.__schema_name__ = kwargs.get("schema_name", _name)
        directive.__extensions__ = kwargs.get("extensions", {})
        directive.__attribute_docstrings__ = parse_class_attribute_docstrings(directive)

        directive.__extensions__[undine_settings.DIRECTIVE_EXTENSIONS_KEY] = directive

        for name, argument in directive.__arguments__.items():
            argument.__connect__(directive, name)  # type: ignore[arg-type]

        # Create the GraphQL directive to register it.
        # This way it shows up in the GraphQL schema automatically.
        directive.__directive__()

        return directive

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_directive(cls.__directive__())

    def __directive__(cls) -> GraphQLDirective:
        """Creates the `GraphQLDirective` for this `Directive`."""
        return get_or_create_graphql_directive(
            name=cls.__schema_name__,
            locations=cls.__locations__,
            args={arg.schema_name: arg.as_graphql_argument() for arg in cls.__arguments__.values()},
            is_repeatable=cls.__is_repeatable__,
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )


class Directive(metaclass=DirectiveMeta):
    """
    A class for creating new Directives to add to GraphQL objects.
    Represents a GraphQL `Directive` in the `Schema`.

    The following parameters can be passed in the class definition:

    `locations: list[DirectiveLocation]`
        Places where this directive can be used. Required.

    `is_repeatable: bool = False`
        Whether the `Directive` is repeatable.

    `schema_name: str = <class name>`
        Override name for the `GraphQLDirective` for this `Directive` in the GraphQL schema.

    `directives`: `list[Directive] = []`
        `Directives` to add to the created `GraphQLDirective`.

    `extensions`: `dict[str, Any] = {}`
        GraphQL extensions for the created `GraphQLDirective`.

    >>> class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `DirectiveArgument` names.

    # Set in metaclass
    __locations__: ClassVar[list[DirectiveLocation]]
    __arguments__: ClassVar[dict[str, DirectiveArgument]]
    __is_repeatable__: ClassVar[bool]
    __schema_name__: ClassVar[str]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    def __init__(self, **kwargs: Any) -> None:
        parameters: dict[str, Any] = {}

        for name, arg in self.__arguments__.items():
            value = kwargs.pop(name, arg.default_value)
            if value is Undefined:
                raise MissingDirectiveArgumentError(name=name, directive=type(self))

            parameters[name] = value

        if kwargs:
            raise UnexpectedDirectiveArgumentError(directive=type(self), kwargs=kwargs)

        self.__parameters__: MappingProxyType[str, Any] = MappingProxyType(parameters)

    def __repr__(self) -> str:
        args = ", ".join(f"{name}={value!r}" for name, value in self.__parameters__.items())
        return f"<{dotpath(self.__class__)}({args})>"

    def __str__(self) -> str:
        return undine_settings.SDL_PRINTER.print_directive_usage(self, indent=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.__parameters__ == other.__parameters__

    def __hash__(self) -> int:
        return hash((type(self), tuple(self.__parameters__.items())))


class DirectiveArgument:
    """
    A class for defining a directive argument.
    Represents an argument on a GraphQL `Directive` for the `Directive` this is added to.

    >>> class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
    ...     name = DirectiveArgument(GraphQLNonNull(GraphQLInt))
    """

    def __init__(self, input_type: GraphQLInputType, **kwargs: Unpack[DirectiveArgumentParams]) -> None:
        """
        Create a new `DirectiveArgument`.

        :param input_type: The input type to use for the `DirectiveArgument`.
        :param description: Description for the `DirectiveArgument`.
        :param default_value: Default value for the `DirectiveArgument`.
        :param deprecation_reason: If the `DirectiveArgument` is deprecated, describes the reason for deprecation.
        :param schema_name: Actual name in the GraphQL schema. Only needed if argument name is a python keyword.
        :param directives: GraphQL directives for the `DirectiveArgument`.
        :param extensions: GraphQL extensions for the `DirectiveArgument`.
        """
        self.input_type = input_type

        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.default_value: DefaultValueType = kwargs.get("default_value", Undefined)
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})

        check_directives(self.directives, location=DirectiveLocation.ARGUMENT_DEFINITION)
        self.extensions[undine_settings.DIRECTIVE_ARGUMENT_EXTENSIONS_KEY] = self

    def __connect__(self, directive: type[Directive], name: str) -> None:
        """Connect this `DirectiveArgument` to the given `Directive` using the given name."""
        self.directive = directive
        self.name = name
        self.schema_name = self.schema_name or to_schema_name(name)

        if self.description is Undefined:
            self.description = self.directive.__attribute_docstrings__.get(name)

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(input_type={self.input_type!r})>"

    def __str__(self) -> str:
        arg = self.as_graphql_argument()
        return undine_settings.SDL_PRINTER.print_directive_argument(self.schema_name, arg, indent=False)

    def as_graphql_argument(self) -> GraphQLArgument:
        return GraphQLArgument(
            type_=self.input_type,
            default_value=self.default_value,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            out_name=self.name,
            extensions=self.extensions,
        )
