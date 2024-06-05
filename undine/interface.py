from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Unpack

from graphql import DirectiveLocation, GraphQLField, Undefined

from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_interface_type
from undine.utils.graphql.utils import check_directives
from undine.utils.reflection import FunctionEqualityWrapper, get_members
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from graphql import GraphQLArgumentMap, GraphQLInterfaceType, GraphQLOutputType

    from undine.directives import Directive
    from undine.query import Field, QueryType
    from undine.typing import GQLInfo, InterfaceFieldParams, InterfaceTypeParams

__all__ = [
    "InterfaceField",
    "InterfaceType",
]


class InterfaceTypeMeta(type):
    """A metaclass that modifies how a `InterfaceType` is created."""

    # Set in '__new__'
    __field_map__: dict[str, InterfaceField]
    __schema_name__: str
    __interfaces__: list[type[InterfaceType]]
    __implementations__: list[type[InterfaceType | QueryType]]
    __directives__: list[Directive]
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[InterfaceTypeParams],
    ) -> InterfaceTypeMeta:
        if _name == "InterfaceType":  # Early return for the `InterfaceType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        interfaces = kwargs.get("interfaces", [])
        for interface in interfaces:
            for field_name, interface_field in interface.__field_map__.items():
                _attrs.setdefault(field_name, interface_field)

        interface_type = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `InterfaceField` names.
        interface_type.__field_map__ = get_members(interface_type, InterfaceField)
        interface_type.__schema_name__ = kwargs.get("schema_name", _name)
        interface_type.__interfaces__ = interfaces
        interface_type.__implementations__ = []
        interface_type.__directives__ = kwargs.get("directives", [])
        interface_type.__extensions__ = kwargs.get("extensions", {})
        interface_type.__attribute_docstrings__ = parse_class_attribute_docstrings(interface_type)

        check_directives(interface_type.__directives__, location=DirectiveLocation.INTERFACE)
        interface_type.__extensions__[undine_settings.INTERFACE_TYPE_EXTENSIONS_KEY] = interface_type

        for interface in interfaces:
            interface.__register_as_implementation__(interface_type)  # type: ignore[arg-type]

        for name, interface_field in interface_type.__field_map__.items():
            interface_field.__connect__(interface_type, name)  # type: ignore[arg-type]

        return interface_type

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_interface_type(cls.__interface__())

    def __register_as_implementation__(cls, implementation: type[InterfaceType | QueryType]) -> None:
        cls.__implementations__.append(implementation)
        for interface in cls.__interfaces__:
            interface.__register_as_implementation__(implementation)

    def __concrete_implementations__(cls) -> list[type[QueryType]]:
        return [impl for impl in cls.__implementations__ if not issubclass(impl, InterfaceType)]  # type: ignore[return-value]

    def __interface__(cls) -> GraphQLInterfaceType:
        return get_or_create_graphql_interface_type(
            name=cls.__schema_name__,
            fields=FunctionEqualityWrapper(cls.__output_fields__, context=cls),
            interfaces=[instance.__interface__() for instance in cls.__interfaces__],
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )

    def __output_fields__(cls) -> dict[str, GraphQLField]:
        """Defer creating fields until all QueryTypes have been registered."""
        return {field.schema_name: field.as_graphql_field() for field in cls.__field_map__.values()}


class InterfaceType(metaclass=InterfaceTypeMeta):
    """
    Class for creating a new `InterfaceType` for a `QueryType`.
    Represents a GraphQL `GraphQLInterfaceType` in the GraphQL schema.

    The following parameters can be passed in the class definition:

     `interfaces: list[type[InterfaceType]] = []`
        Interfaces this `InterfaceType` should implement.

     `schema_name: str = <class name>`
        Override name for the `GraphQLInterfaceType` for this `InterfaceType` in the GraphQL schema.

     `directives: list[Directive] = []`
        `Directives` to add to the created `GraphQLInterfaceType`.

     `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `GraphQLInterfaceType`.

    >>> class Node(InterfaceType)
    >>>     id = InterfaceField(GraphQLNonNull(GraphQLID), resolvable_output_type=True)
    """

    # Set in metaclass
    __field_map__: ClassVar[dict[str, InterfaceField]]
    __schema_name__: ClassVar[str]
    __interfaces__: ClassVar[list[type[InterfaceType]]]
    __implementations__: ClassVar[list[type[InterfaceType | QueryType]]]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    @classmethod
    def __process_results__(cls, instances: list[Any], info: GQLInfo) -> list[Any]:
        """Filter and order results of the interface after everything has been fetched."""
        return instances


class InterfaceField:
    """
    A class for defining a field for an `InterfaceType`.
    Represents a field on a GraphQL `Interface` for the `InterfaceType` this is added to.

    >>> class Node(InterfaceType):
    >>>     id = InterfaceField(GraphQLNonNull(GraphQLID), resolvable_output_type=True)
    """

    def __init__(self, output_type: GraphQLOutputType, **kwargs: Unpack[InterfaceFieldParams]) -> None:
        """
        Create a new `InterfaceField`.

        :param output_type: The output type to use for the `InterfaceField`.
        :param args: GraphQL arguments for the `InterfaceField`.
        :param resolvable_output_type: If True, the output type will be used as the reference of a `Field`
                                       when the `InterfaceType` is added to a `QueryType`.
        :param description: Description for the `InterfaceField`.
        :param deprecation_reason: If the `InterfaceField` is deprecated, describes the reason for deprecation.
        :param schema_name: Actual name in the GraphQL schema. Only needed if argument name is a python keyword.
        :param directives: GraphQL directives for the `InterfaceField`.
        :param extensions: GraphQL extensions for the `InterfaceField`.
        """
        self.output_type = output_type

        self.args: GraphQLArgumentMap = kwargs.get("args", {})
        self.resolvable_output_type: bool = kwargs.get("resolvable_output_type", False)
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})

        check_directives(self.directives, location=DirectiveLocation.FIELD_DEFINITION)
        self.extensions[undine_settings.INTERFACE_FIELD_EXTENSIONS_KEY] = self

    def __connect__(self, interface_type: type[InterfaceType], name: str) -> None:
        """Connect this `InterfaceField` to the given `InterfaceType` using the given name."""
        self.interface_type = interface_type
        self.name = name
        self.schema_name = self.schema_name or to_schema_name(name)

        if self.description is Undefined:
            self.description = interface_type.__attribute_docstrings__.get(name)

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.output_type!r})>"

    def __str__(self) -> str:
        field = self.as_graphql_field()
        return undine_settings.SDL_PRINTER.print_field(self.schema_name, field, indent=False)

    def as_graphql_field(self) -> GraphQLField:
        return GraphQLField(
            type_=self.output_type,
            args=self.args,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def as_undine_field(self) -> Field:
        """Convert this `InterfaceField` to a `Field` to be added to a `QueryType`."""
        from undine.query import Field  # noqa: PLC0415

        return Field(
            self.output_type if self.resolvable_output_type else None,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            schema_name=self.schema_name,
            directives=self.directives,
        )
