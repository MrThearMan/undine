from __future__ import annotations

from collections import UserList
from typing import TYPE_CHECKING, Any, ClassVar, Self, Unpack

from graphql import DirectiveLocation, GraphQLArgument, GraphQLBoolean, GraphQLInt, GraphQLNonNull, Undefined

from undine.converters import convert_to_graphql_type
from undine.dataclasses import TypeRef
from undine.exceptions import (
    MissingDirectiveArgumentError,
    MissingDirectiveLocationsError,
    NotCompatibleWithError,
    UnexpectedDirectiveArgumentError,
)
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import DIRECTIVE_REGISTRY, get_or_create_graphql_directive
from undine.utils.graphql.utils import check_directives
from undine.utils.reflection import get_members, get_wrapped_func
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graphql import GraphQLDirective, GraphQLInputType

    from undine import CalculationArgument, Entrypoint, Field, Filter, Order
    from undine.entrypoint import RootType, RootTypeMeta
    from undine.filtering import FilterSetMeta
    from undine.interface import InterfaceField, InterfaceType, InterfaceTypeMeta
    from undine.mutation import MutationTypeMeta
    from undine.ordering import OrderSetMeta
    from undine.query import QueryType, QueryTypeMeta
    from undine.typing import (
        DefaultValueType,
        DirectiveArgumentParams,
        DirectiveParams,
        DjangoRequestProtocol,
        T,
        VisibilityFunc,
    )
    from undine.union import UnionType, UnionTypeMeta

__all__ = [
    "AtomicDirective",
    "CacheRulesDirective",
    "ComplexityDirective",
    "Directive",
    "DirectiveArgument",
    "DirectiveList",
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

        # Set the directive to the directive registry so that it shows up in the GraphQL schema automatically.
        DIRECTIVE_REGISTRY[directive.__schema_name__] = directive  # type: ignore[assignment]

        return directive

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_directive(cls.__directive__())

    def __contains__(cls, item: str) -> bool:
        return item in cls.__arguments__

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

        self.__parameters__ = parameters

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        """
        Determine if the given `Directive` is visible in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.
        """
        return True

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

    def __call__(self, other: T, /) -> T:
        """
        Allow adding directives using decorators.

        >>> class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...
        >>>
        >>> @MyDirective()
        >>> class TaskType(QueryType[Task]): ...
        """
        self.__connect__(other)
        return other

    def __rmatmul__(self, other: T) -> T:
        """
        Allow adding directives using the @ operator.

        >>> class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...
        >>>
        >>> class TaskType(QueryType[Task]):
        >>>     name = Field() @ MyDirective()
        """
        self.__connect__(other)
        return other

    def __connect__(self, other: Any) -> None:
        if isinstance(getattr(other, "directives", None), DirectiveList):
            other: CalculationArgument | Entrypoint | Field | Filter | Order
            other.directives.append(self)
            self.__connected__(other)
            return

        if isinstance(getattr(other, "__directives__", None), DirectiveList):
            other: (
                FilterSetMeta
                | InterfaceTypeMeta
                | MutationTypeMeta
                | OrderSetMeta
                | QueryTypeMeta
                | RootTypeMeta
                | UnionTypeMeta
            )
            other.__directives__.append(self)
            self.__connected__(other)
            return

        raise NotCompatibleWithError(obj=self, other=other)

    def __connected__(self, other: Any) -> None:
        """A hook that is called to connect this directive to an object."""


class DirectiveArgument:
    """
    A class for defining a directive argument.
    Represents an argument on a GraphQL `Directive` for the `Directive` this is added to.

    >>> class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
    ...     name = DirectiveArgument(GraphQLNonNull(GraphQLInt))
    """

    def __init__(self, ref: Any, **kwargs: Unpack[DirectiveArgumentParams]) -> None:
        """
        Create a new `DirectiveArgument`.

        :param ref: Reference to use for the `DirectiveArgument`.
        :param description: Description for the `DirectiveArgument`.
        :param default_value: Default value for the `DirectiveArgument`.
        :param deprecation_reason: If the `DirectiveArgument` is deprecated, describes the reason for deprecation.
        :param schema_name: Actual name in the GraphQL schema. Only needed if argument name is a python keyword.
        :param directives: GraphQL directives for the `DirectiveArgument`.
        :param extensions: GraphQL extensions for the `DirectiveArgument`.
        """
        self.ref: Any = ref

        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.default_value: DefaultValueType = kwargs.get("default_value", Undefined)
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]

        directives = kwargs.get("directives", [])
        self.directives = DirectiveList(directives, location=DirectiveLocation.ARGUMENT_DEFINITION)

        self.extensions: dict[str, Any] = kwargs.get("extensions", {})
        self.extensions[undine_settings.DIRECTIVE_ARGUMENT_EXTENSIONS_KEY] = self

        self.visible_func: VisibilityFunc | None = None

    def __connect__(self, directive: type[Directive], name: str) -> None:
        """Connect this `DirectiveArgument` to the given `Directive` using the given name."""
        self.directive = directive
        self.name = name
        self.schema_name = self.schema_name or to_schema_name(name)

        if self.description is Undefined:
            self.description = self.directive.__attribute_docstrings__.get(name)

        for directive_ in self.directives:
            directive_.__connected__(self)

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref!r})>"

    def __str__(self) -> str:
        arg = self.as_graphql_argument()
        return undine_settings.SDL_PRINTER.print_directive_argument(self.schema_name, arg, indent=False)

    def __get__(self, instance: Directive | None, cls: type[Directive]) -> Any:
        if instance is None:
            return self
        return instance.__parameters__[self.name]

    def __set__(self, instance: Directive | None, value: Any) -> None:
        if instance is None:
            msg = f"Can't set attribute {self.name} on {type(self).__name__}"
            raise AttributeError(msg)
        instance.__parameters__[self.name] = value

    def get_argument_type(self) -> GraphQLInputType:
        return convert_to_graphql_type(TypeRef(value=self.ref), model=None, is_input=True)

    def as_graphql_argument(self) -> GraphQLArgument:
        return GraphQLArgument(
            type_=self.get_argument_type(),
            default_value=self.default_value,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            out_name=self.name,
            extensions=self.extensions,
        )

    def visible(self, func: VisibilityFunc | None = None, /) -> VisibilityFunc:
        """
        Decorate a function to change the DirectiveArgument's visibility in the schema.

        >>> class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        ...     name = DirectiveArgument(GraphQLNonNull(GraphQLString))
        ...
        ...     @name.visible
        ...     def name_visible(self: DirectiveArgument, request: DjangoRequestProtocol) -> bool:
        ...         return False
        """
        if func is None:  # Allow `@<directive_argument_name>.visible()`
            return self.visible  # type: ignore[return-value]
        self.visible_func = get_wrapped_func(func)
        return func


class DirectiveList(UserList[Directive]):
    """A list of directives for a certain location. Checks directives each time they are added."""

    # List API

    def __init__(self, directives: Iterable[Directive], *, location: DirectiveLocation) -> None:
        self.location = location
        self.__check_directives(directives)
        super().__init__(directives)

    def __setitem__(self, index: int, value: Directive) -> None:
        data = self.data[:]
        data[index] = value
        self.__check_directives(data)
        self.data = data

    def __add__(self, other: Iterable[Directive]) -> DirectiveList:
        data = self.data + self.__get_other_data(other)
        self.__check_directives(data)
        return self.__class__(data, location=self.location)

    __radd__ = __add__

    def __iadd__(self, other: Iterable[Directive]) -> Self:
        data = self.data + self.__get_other_data(other)
        self.__check_directives(data)
        self.data = data
        return self

    def __mul__(self, other: int) -> DirectiveList:
        data = self.data * other
        self.__check_directives(data)
        return self.__class__(data, location=self.location)

    __rmul__ = __mul__

    def __imul__(self, other: int) -> Self:
        data = self.data * other
        self.__check_directives(data)
        self.data = data
        return self

    def append(self, value: Directive) -> None:
        data = [*self.data, value]
        self.__check_directives(data)
        self.data = data

    def insert(self, index: int, value: Directive) -> None:
        data = self.data[:]
        data.insert(index, value)
        self.__check_directives(data)
        self.data = data

    def extend(self, other: Iterable[Directive]) -> None:
        data = self.data + self.__get_other_data(other)
        self.__check_directives(data)
        self.data = data

    # Custom methods

    def __check_directives(self, directives: Iterable[Directive]) -> None:
        check_directives(directives, location=self.location)

    def __get_other_data(self, other: Iterable[Directive]) -> list[Any]:
        if isinstance(other, UserList):
            return other.data
        if isinstance(other, type(self.data)):
            return other
        return list(other)


# Built-in directives


class AtomicDirective(
    Directive,
    locations=[DirectiveLocation.MUTATION],
    schema_name="atomic",
):
    """Used to indicate that all mutations in the operation should be executed atomically."""


class ComplexityDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION],
    schema_name="complexity",
):
    """
    Used to indicate the complexity of resolving a field, counted towards
    the maximum query complexity of resolving a root type field.
    """

    value = DirectiveArgument(GraphQLNonNull(GraphQLInt), description="The complexity of resolving the field.")

    def __init__(self, *, value: int) -> None:
        """
        Create a new `ComplexityDirective`.

        :param value: The complexity of resolving the field.
        """
        if value < 0:
            msg = "`value` must be a positive integer."
            raise ValueError(msg)
        super().__init__(value=value)

    def __connected__(self, other: Any) -> None:
        if hasattr(other, "complexity"):
            other: Field | Entrypoint
            other.complexity = self.value


class CacheRulesDirective(
    Directive,
    locations=[
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.OBJECT,
        DirectiveLocation.INTERFACE,
        DirectiveLocation.UNION,
    ],
    schema_name="cacheRules",
):
    """Used to define caching behavior either for a single field, or for all fields that return a particular type."""

    cache_time = DirectiveArgument(
        GraphQLNonNull(GraphQLInt),
        description="How many seconds this field of fields of this type can be cached for.",
    )

    cache_per_user = DirectiveArgument(
        GraphQLNonNull(GraphQLBoolean),
        default_value=False,
        description="Whether the value is cached per user or not.",
    )

    def __init__(self, *, cache_time: int = Undefined, cache_per_user: bool = False) -> None:
        """
        Create a new `CacheDirective`.

        :param cache_time: How many seconds this field of fields of this type can be cached for.
                           I undefined, a default value is used.
                           For an `Entrypoint`, the value is set by `ENTRYPOINT_DEFAULT_CACHE_TIME`.
                           For a `Field`, the value is inherited from the parent.
        :param cache_per_user: Whether the value is cached per user or not.
        """
        if isinstance(cache_time, int) and cache_time < 0:
            msg = "`cache_time` must be a positive integer."
            raise ValueError(msg)

        super().__init__(cache_time=cache_time, cache_per_user=cache_per_user)

    def __connected__(self, other: Any) -> None:
        from undine import Entrypoint  # noqa: PLC0415

        if self.cache_time is Undefined:
            if isinstance(other, Entrypoint):
                self.cache_time = undine_settings.ENTRYPOINT_DEFAULT_CACHE_TIME
            else:
                self.cache_time = None  # Inherit from parent

        if hasattr(other, "cache_time"):
            other: Entrypoint | Field | InterfaceField
            other.cache_time = self.cache_time
            other.cache_per_user = self.cache_per_user
            return

        if hasattr(other, "__cache_time__"):
            other: RootType | QueryType | InterfaceType | UnionType
            other.__cache_time__ = self.cache_time
            other.__cache_per_user__ = self.cache_per_user
            return
