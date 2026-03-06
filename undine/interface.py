from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, ClassVar, Unpack

from graphql import DirectiveLocation, GraphQLField, Undefined

from undine.converters import convert_to_graphql_argument_map, convert_to_graphql_type, is_many
from undine.dataclasses import TypeRef
from undine.directives import CacheDirective, ComplexityDirective, DirectiveList
from undine.exceptions import InterfaceFieldTypeMismatchError
from undine.parsers import parse_class_attribute_docstrings
from undine.query import QueryType
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_interface_type
from undine.utils.reflection import FunctionEqualityWrapper, get_members, get_wrapped_func, is_subclass
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from graphql import GraphQLArgumentMap, GraphQLInterfaceType, GraphQLOutputType

    from undine.query import Field
    from undine.typing import (
        DjangoRequestProtocol,
        InterfaceFieldParams,
        InterfaceTypeParams,
        TInterfaceQueryType,
        VisibilityFunc,
    )

__all__ = [
    "InterfaceField",
    "InterfaceType",
]


class InterfaceTypeMeta(type):
    """A metaclass that modifies how a `InterfaceType` is created."""

    # Set in '__new__'
    __field_map__: dict[str, InterfaceField]
    __schema_name__: str
    __cache_for_seconds__: int | None
    __cache_per_user__: bool
    __interfaces__: list[type[InterfaceType]]
    __implementations__: list[type[InterfaceType | QueryType]]
    __directives__: DirectiveList
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
        interfaces = get_with_inherited_interfaces(interfaces)

        interface_type = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `InterfaceField` names.
        interface_type.__field_map__ = get_members(interface_type, InterfaceField)
        interface_type.__schema_name__ = kwargs.get("schema_name", _name)
        interface_type.__attribute_docstrings__ = parse_class_attribute_docstrings(interface_type)
        interface_type.__cache_for_seconds__ = kwargs.get("cache_for_seconds")
        interface_type.__cache_per_user__ = kwargs.get("cache_per_user", False)

        interface_type.__interfaces__ = []
        interface_type.__implementations__ = []

        directives = kwargs.get("directives", [])
        interface_type.__directives__ = DirectiveList(directives, location=DirectiveLocation.INTERFACE)

        interface_type.__extensions__ = kwargs.get("extensions", {})
        interface_type.__extensions__[undine_settings.INTERFACE_TYPE_EXTENSIONS_KEY] = interface_type

        for name, interface_field in interface_type.__field_map__.items():
            interface_field.__connect__(interface_type, name)  # type: ignore[arg-type]

        for interface in interfaces:
            interface.__inherit__(interface_type)  # type: ignore[arg-type]

        for directive in interface_type.__directives__:
            directive.__connected__(interface_type)

        return interface_type

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_interface_type(cls.__interface__())

    def __contains__(cls, item: str) -> bool:
        return item in cls.__field_map__

    def __call__(cls, implementation: type[TInterfaceQueryType]) -> type[TInterfaceQueryType]:
        """
        Allow iheriting this InterfaceType to a QueryType or another InterfaceType using a decorator syntax.

        >>> class Named(InterfaceType): ...
        >>>
        >>> @Named
        >>> class TaskType(QueryType[Task]): ...
        """
        cls.__inherit__(implementation)
        return implementation

    def __inherit__(cls, implementation: type[TInterfaceQueryType]) -> None:
        """Make the given `QueryType` or `InterfaceType` inherit from this `InterfaceType`."""
        if is_subclass(implementation, QueryType):
            for field_name, interface_field in cls.__field_map__.items():
                existing = implementation.__field_map__.get(field_name)
                if existing is not None:
                    interface_field.check_inheritance(existing)
                    continue

                field = interface_field.as_undine_field()
                setattr(implementation, field_name, field)
                implementation.__field_map__[field_name] = field
                field.__connect__(implementation, field_name)
                interface_field.check_inheritance(field)

        elif is_subclass(implementation, InterfaceType):
            for field_name, interface_field in cls.__field_map__.items():
                existing = implementation.__field_map__.get(field_name)
                if existing is not None:
                    interface_field.check_inheritance(existing)
                    continue

                copy_field = copy.deepcopy(interface_field)
                setattr(implementation, field_name, copy_field)
                implementation.__field_map__[field_name] = copy_field
                copy_field.__connect__(implementation, field_name)

        implementation.__interfaces__.append(cls)  # type: ignore[assignment]
        cls.__register_as_implementation__(implementation)

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

     `cache_for_seconds: int | None = None`
        How many seconds this `InterfaceType` can be cached for.

     `cache_per_user: bool = False`
        Whether the `InterfaceType` is cached per user or not.

     `schema_name: str = <class name>`
        Override name for the `GraphQLInterfaceType` for this `InterfaceType` in the GraphQL schema.

     `directives: list[Directive] = []`
        `Directives` to add to the created `GraphQLInterfaceType`.

     `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `GraphQLInterfaceType`.

    >>> class Named(InterfaceType)
    >>>     name = InterfaceField(GraphQLNonNull(GraphQLString))
    """

    # Set in metaclass
    __field_map__: ClassVar[dict[str, InterfaceField]]
    __schema_name__: ClassVar[str]
    __cache_for_seconds__: ClassVar[int | None]
    __cache_per_user__: ClassVar[bool]
    __interfaces__: ClassVar[list[type[InterfaceType]]]
    __implementations__: ClassVar[list[type[InterfaceType | QueryType]]]
    __directives__: ClassVar[DirectiveList]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        """
        Determine if the given `InterfaceType` is visible in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.
        """
        return True


class InterfaceField:
    """
    A class for defining a field for an `InterfaceType`.
    Represents a field on a GraphQL `Interface` for the `InterfaceType` this is added to.

    >>> class Named(InterfaceType):
    ...     name = InterfaceField(GraphQLNonNull(GraphQLString))
    """

    def __init__(self, ref: Any, **kwargs: Unpack[InterfaceFieldParams]) -> None:
        """
        Create a new `InterfaceField`.

        :param ref: The reference to use for the `InterfaceField`.
        :param description: Description for the `InterfaceField`.
        :param deprecation_reason: If the `InterfaceField` is deprecated, describes the reason for deprecation.
        :param complexity: The complexity of resolving this `InterfaceField`.
        :param cache_for_seconds: How many seconds this `InterfaceField` can be cached for.
        :param cache_per_user: Whether the `InterfaceField` is cached per user or not.
        :param field_name: The name of the field in the Django model. If not provided, use the name of the attribute.
        :param schema_name: Actual name in the GraphQL schema. Only needed if argument name is a python keyword.
        :param directives: GraphQL directives for the `InterfaceField`.
        :param extensions: GraphQL extensions for the `InterfaceField`.
        """
        self.ref = ref

        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.complexity: int = kwargs.get("complexity", Undefined)  # type: ignore[assignment]
        self.cache_for_seconds: int | None = kwargs.get("cache_for_seconds")
        self.cache_per_user: bool = kwargs.get("cache_per_user", False)
        self.field_name: str = kwargs.get("field_name", Undefined)  # type: ignore[assignment]
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]

        directives = kwargs.get("directives", [])
        if self.complexity:
            directives.append(ComplexityDirective(value=self.complexity))
        if self.cache_for_seconds is not None:
            directives.append(CacheDirective(for_seconds=self.cache_for_seconds, per_user=self.cache_per_user))

        self.directives = DirectiveList(directives, location=DirectiveLocation.FIELD_DEFINITION)

        self.extensions: dict[str, Any] = kwargs.get("extensions", {})
        self.extensions[undine_settings.INTERFACE_FIELD_EXTENSIONS_KEY] = self

        self.visible_func: VisibilityFunc | None = None

    def __connect__(self, interface_type: type[InterfaceType], name: str) -> None:
        """Connect this `InterfaceField` to the given `InterfaceType` using the given name."""
        self.interface_type = interface_type
        self.name = name
        self.field_name = self.field_name or name
        self.schema_name = self.schema_name or to_schema_name(name)

        if self.description is Undefined:
            self.description = interface_type.__attribute_docstrings__.get(name)

        for directive in self.directives:
            directive.__connected__(self)

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref!r})>"

    def __str__(self) -> str:
        field = self.as_graphql_field()
        return undine_settings.SDL_PRINTER.print_field(self.schema_name, field, indent=False)

    def get_field_type(self) -> GraphQLOutputType:
        return convert_to_graphql_type(TypeRef(value=self.ref))

    def get_field_arguments(self) -> GraphQLArgumentMap | None:
        many = is_many(self.ref, name=self.field_name)
        return convert_to_graphql_argument_map(self.ref, many=many)

    def as_graphql_field(self) -> GraphQLField:
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def as_undine_field(self) -> Field:
        """Convert this `InterfaceField` to a `Field` to be added to a `QueryType`."""
        from undine.query import Field  # noqa: PLC0415

        return Field(
            self,
            deprecation_reason=self.deprecation_reason,
            complexity=self.complexity,
            cache_for_seconds=self.cache_for_seconds,
            cache_per_user=self.cache_per_user,
            field_name=self.field_name,
            schema_name=self.schema_name,
            extensions={undine_settings.INTERFACE_FIELD_EXTENSIONS_KEY: self},
        )

    def visible(self, func: VisibilityFunc | None = None, /) -> VisibilityFunc:
        """
        Decorate a function to change the InterfaceField's visibility in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.

        >>> class Named(InterfaceType):
        ...     name = InterfaceField(GraphQLNonNull(GraphQLString))
        ...
        ...     @name.visible
        ...     def name_visible(self: InterfaceField, request: DjangoRequestProtocol) -> bool:
        ...         return False
        """
        if func is None:  # Allow `@<interface_field_name>.visible()`
            return self.visible  # type: ignore[return-value]
        self.visible_func = get_wrapped_func(func)
        return func

    def check_inheritance(self, field: Field | InterfaceField) -> None:
        """Check that given type and arguments satisfy the requirements of this `InterfaceField`."""
        field_type = field.get_field_type()
        if self.get_field_type() == field_type and self.get_field_arguments() == field.get_field_arguments():
            return

        raise InterfaceFieldTypeMismatchError(
            field=self.schema_name,
            interface=self.interface_type,
            output_type=self.ref,
            field_type=field_type,
        )


def get_with_inherited_interfaces(interfaces: list[type[InterfaceType]]) -> list[type[InterfaceType]]:
    """
    Given the list of interfaces that an `InterfaceType` might explicitly inherit,
    add all implicitly inherited interfaces to the list (e.g. interfaces of interfaces).
    """
    all_interfaces: set[type[InterfaceType]] = set()

    for interface in interfaces:
        if interface in all_interfaces:
            continue

        all_interfaces.add(interface)
        all_interfaces.update(get_with_inherited_interfaces(interface.__interfaces__))

    return list(all_interfaces)
