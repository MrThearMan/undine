from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any, ClassVar, Unpack

from graphql import DirectiveLocation, GraphQLField, Undefined

from undine.converters import (
    convert_to_description,
    convert_to_entrypoint_resolver,
    convert_to_graphql_argument_map,
    convert_to_graphql_type,
    is_many,
)
from undine.dataclasses import MaybeManyOrNonNull
from undine.exceptions import MissingEntrypointRefError
from undine.parsers import parse_class_attribute_docstrings, parse_is_nullable
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type
from undine.utils.graphql.utils import check_directives
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members, get_wrapped_func
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from graphql import GraphQLArgumentMap, GraphQLFieldResolver, GraphQLObjectType, GraphQLOutputType

    from undine.directives import Directive
    from undine.typing import EntrypointParams, PermissionFunc, RootTypeParams

__all__ = [
    "Entrypoint",
    "RootType",
]


class RootTypeMeta(type):
    """A metaclass that modifies how a `RootType` is created."""

    # Set in '__new__'
    __entrypoint_map__: dict[str, Entrypoint]
    __schema_name__: str
    __directives__: list[Directive]
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[RootTypeParams],
    ) -> RootTypeMeta:
        if _name == "RootType":  # Early return for the `RootType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        root_type = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `Entrypoint` names.
        root_type.__entrypoint_map__ = get_members(root_type, Entrypoint)
        root_type.__schema_name__ = kwargs.get("schema_name", _name)
        root_type.__directives__ = kwargs.get("directives", [])
        root_type.__extensions__ = kwargs.get("extensions", {})
        root_type.__attribute_docstrings__ = parse_class_attribute_docstrings(root_type)

        check_directives(root_type.__directives__, location=DirectiveLocation.OBJECT)
        root_type.__extensions__[undine_settings.ROOT_TYPE_EXTENSIONS_KEY] = root_type

        for name, entrypoint in root_type.__entrypoint_map__.items():
            entrypoint.__connect__(root_type, name)  # type: ignore[arg-type]

        return root_type

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_object_type(cls.__output_type__())

    def __output_type__(cls) -> GraphQLObjectType:
        """Creates the GraphQL `ObjectType` for this `RootType`."""
        return get_or_create_graphql_object_type(
            name=cls.__schema_name__,
            fields=FunctionEqualityWrapper(cls.__output_fields__, context=cls),
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )

    def __output_fields__(cls) -> dict[str, GraphQLField]:
        return {
            entrypoint.schema_name: entrypoint.as_graphql_field()  # ...
            for entrypoint in cls.__entrypoint_map__.values()
        }


class RootType(metaclass=RootTypeMeta):
    """
    A class for creating a new `RootType` with `Entrypoints`.
    Represents a GraphQL `GraphQLObjectType` at the root of the GraphQL schema.

    The following parameters can be passed in the class definition:

    `schema_name: str = <class name>`
        Override name for the `ObjectType` for this `RootType` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `ObjectType`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `ObjectType`.

    >>> class TaskType(QueryType[Task]): ...
    >>>
    >>> class Query(RootType):
    ...     tasks = Entrypoint(TaskType, many=True)
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `Entrypoint` names.

    # Set in metaclass
    __entrypoint_map__: ClassVar[dict[str, Entrypoint]]
    __schema_name__: ClassVar[str]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]


class Entrypoint:
    """
    A class for creating new fields in the `RootTypes` of the GraphQL schema.
    These are the "entry points" at the top level of the GraphQL schema.

    >>> class TaskType(QueryType[Task]): ...
    >>>
    >>> class Query(RootType):
    ...     tasks = Entrypoint(TaskType, many=True)
    """

    def __init__(self, ref: Any = Undefined, **kwargs: Unpack[EntrypointParams]) -> None:
        """
        Create a new `Entrypoint`.

        :param ref: The reference to use for the `Entrypoint`.
        :param many: Whether the `Entrypoint` should return a non-null list of the referenced type.
        :param nullable: Whether the referenced type can be null.
        :param limit: For `UnionTypes` and `InterfaceTypes`, limits the number of objects that are fetched.
        :param description: Description for the `Entrypoint`.
        :param deprecation_reason: If the `Entrypoint` is deprecated, describes the reason for deprecation.
        :param schema_name: Actual name in the GraphQL schema. Only needed if argument name is a python keyword.
        :param directives: GraphQL directives for the `Entrypoint`.
        :param extensions: GraphQL extensions for the `Entrypoint`.
        """
        self.ref: Any = cache_signature_if_function(ref, depth=1)

        self.many: bool = kwargs.get("many", False)
        self.nullable: bool = kwargs.get("nullable", False)
        self.limit: int = kwargs.get("limit", undine_settings.ENTRYPOINT_LIMIT_PER_MODEL)
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})

        check_directives(self.directives, location=DirectiveLocation.FIELD_DEFINITION)
        self.extensions[undine_settings.ENTRYPOINT_EXTENSIONS_KEY] = self

        self.permissions_func: PermissionFunc | None = None

    def __connect__(self, root_type: type[RootType], name: str) -> None:
        """Connect this `Entrypoint` to the given `RootType` using the given name."""
        self.root_type = root_type
        self.name = name
        self.schema_name = self.schema_name or to_schema_name(name)

        if self.ref is Undefined:
            raise MissingEntrypointRefError(name=name, cls=root_type)

        if isinstance(self.ref, FunctionType):
            self.many = is_many(self.ref)
            self.nullable = parse_is_nullable(self.ref)

        if self.description is Undefined:
            self.description = self.root_type.__attribute_docstrings__.get(name)
            if self.description is None:
                self.description = convert_to_description(self.ref)

    def __call__(self, ref: GraphQLFieldResolver, /) -> Entrypoint:
        """Called when using as decorator with parenthesis: @Entrypoint()"""
        self.ref = cache_signature_if_function(ref, depth=1)
        return self

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref!r})>"

    def __str__(self) -> str:
        field = self.as_graphql_field()
        return undine_settings.SDL_PRINTER.print_field(self.schema_name, field, indent=False)

    def as_graphql_field(self) -> GraphQLField:
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(),
            resolve=self.get_resolver(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLOutputType:
        value = MaybeManyOrNonNull(self.ref, many=self.many, nullable=self.nullable)
        return convert_to_graphql_type(value)  # type: ignore[return-value]

    def get_field_arguments(self) -> GraphQLArgumentMap:
        return convert_to_graphql_argument_map(self.ref, many=self.many, entrypoint=True)

    def get_resolver(self) -> GraphQLFieldResolver:
        return convert_to_entrypoint_resolver(self.ref, caller=self)

    def permissions(self, func: PermissionFunc | None = None, /) -> PermissionFunc:
        """Decorate a function to add it as a permission check for this Entrypoint."""
        if func is None:  # Allow `@<entrypoint_name>.permissions()`
            return self.permissions  # type: ignore[return-value]
        self.permissions_func = get_wrapped_func(func)
        return func
