from __future__ import annotations

import dataclasses
import inspect
from typing import TYPE_CHECKING, Any, ClassVar, Self, Unpack

from graphql import (  # noqa: TC002
    DirectiveLocation,
    GraphQLArgumentMap,
    GraphQLField,
    GraphQLObjectType,
    GraphQLOutputType,
    Undefined,
)

from undine.converters import (
    convert_to_description,
    convert_to_federation_field_ref,
    convert_to_federation_field_resolver,
    convert_to_graphql_argument_map,
    convert_to_graphql_type,
    is_many,
)
from undine.dataclasses import MaybeManyOrNonNull
from undine.directives import DirectiveList
from undine.exceptions import GraphQLFieldNotNullableError
from undine.parsers import parse_class_attribute_docstrings, parse_is_nullable
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type
from undine.utils.reflection import (
    FunctionEqualityWrapper,
    cache_signature_if_function,
    get_members,
    get_root_and_info_params,
    get_wrapped_func,
)
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FunctionType

    from graphql import GraphQLFieldResolver
    from graphql.pyutils import AwaitableOrValue

    from undine.typing import (
        DjangoRequestProtocol,
        FederationFieldParams,
        FederationFieldPermFunc,
        FederationTypeParams,
        GQLInfo,
        VisibilityFunc,
    )

__all__ = [
    "FederationField",
    "FederationType",
]


class FederationTypeMeta(type):
    """A metaclass that modifies how a `FederationType` is created."""

    # Set in '__new__'
    __field_map__: dict[str, FederationField]
    __schema_name__: str
    __directives__: DirectiveList
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[FederationTypeParams],
    ) -> FederationTypeMeta:
        if _name == "FederationType":  # Early return for the `FederationType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        federation_type = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `FederationField` names.
        federation_type.__field_map__ = get_members(federation_type, FederationField)
        federation_type.__schema_name__ = kwargs.get("schema_name", _name)
        federation_type.__attribute_docstrings__ = parse_class_attribute_docstrings(federation_type)

        directives = kwargs.get("directives", [])
        federation_type.__directives__ = DirectiveList(directives, location=DirectiveLocation.OBJECT)

        federation_type.__extensions__ = kwargs.get("extensions", {})
        federation_type.__extensions__[undine_settings.FEDERATION_TYPE_EXTENSIONS_KEY] = federation_type

        FEDERATION_TYPE_REGISTRY[federation_type.__schema_name__] = federation_type  # type: ignore[assignment]

        for name, field in federation_type.__field_map__.items():
            field.__connect__(federation_type, name)  # type: ignore[arg-type]

        for directive in federation_type.__directives__:
            directive.__connected__(federation_type)

        return federation_type

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_object_type(cls.__output_type__())

    def __contains__(cls, item: str) -> bool:
        return item in cls.__field_map__

    def __output_type__(cls) -> GraphQLObjectType:
        """Creates a GraphQL `ObjectType` for this `FederationType`."""
        return get_or_create_graphql_object_type(
            name=cls.__schema_name__,
            fields=FunctionEqualityWrapper(cls.__output_fields__, context=cls),
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )

    def __output_fields__(cls) -> dict[str, GraphQLField]:
        return {field.schema_name: field.as_graphql_field() for field in cls.__field_map__.values()}


class FederationType(metaclass=FederationTypeMeta):
    """
    A class for contributing extra fields to an entity that is owned by another subgraph,
    or for declaring a non-resolvable stub reference to such an entity.

    The following parameters can be passed in the class definition:

    `schema_name: str = <class name>`
        Override name for the `ObjectType` for this `FederationType` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `ObjectType`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `ObjectType`.

    Must be decorated with at least one `@KeyDirective(fields=...)`.

    >>> @KeyDirective(fields="isbn")
    >>> class BookType(FederationType):
    ...     isbn = FederationField(str)
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `FederationField` names.

    # Set in metaclass
    __field_map__: ClassVar[dict[str, FederationField]]
    __schema_name__: ClassVar[str]
    __directives__: ClassVar[DirectiveList]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    def __init__(self, **kwargs: Any) -> None:
        # Untyped kwarg passthrough — the mypy plugin enforces valid kwargs statically.
        self.__parameters__ = dict(kwargs)

    def __repr__(self) -> str:
        args = ", ".join(f"{name}={value!r}" for name, value in self.__parameters__.items())
        return f"<{dotpath(self.__class__)}({args})>"

    @classmethod
    def __permissions__(cls, instance: Self, info: GQLInfo) -> None:
        """Check permissions for accessing an instance through this `FederationType`."""

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        """Determine if the given `FederationType` is visible in the schema."""
        return True


class FederationField:
    """
    A class for defining a field on a `FederationType`.

    >>> @KeyDirective(fields="isbn")
    >>> class BookType(FederationType):
    ...     isbn = FederationField(str)
    """

    def __init__(self, ref: Any = Undefined, **kwargs: Unpack[FederationFieldParams]) -> None:
        """
        Create a new FederationField.

        :param ref: Reference to build the `FederationField` from.
                    Must be convertable by the `convert_to_federation_field_ref` function.
        :param many: Whether the `FederationField` should return a non-null list of the referenced type.
        :param nullable: Whether the referenced type can be null.
        :param description: Description for the `FederationField`.
        :param deprecation_reason: If the `FederationField` is deprecated, describes the reason.
        :param schema_name: Actual name of the `FederationField` in the GraphQL schema.
        :param directives: GraphQL directives for the `FederationField`.
        :param extensions: GraphQL extensions for the `FederationField`.
        """
        self.ref: Any = cache_signature_if_function(ref, depth=1)

        self.many: bool = kwargs.get("many", Undefined)  # type: ignore[assignment]
        self.nullable: bool = kwargs.get("nullable", Undefined)  # type: ignore[assignment]
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]

        directives = kwargs.get("directives", [])
        self.directives = DirectiveList(directives, location=DirectiveLocation.FIELD_DEFINITION)

        self.extensions: dict[str, Any] = kwargs.get("extensions", {})
        self.extensions[undine_settings.FEDERATION_FIELD_EXTENSIONS_KEY] = self

        self.resolver_func: GraphQLFieldResolver | None = None
        self.permissions_func: FederationFieldPermFunc | None = None
        self.visible_func: VisibilityFunc | None = None

    def __connect__(self, federation_type: type[FederationType], name: str) -> None:
        """Connect this `FederationField` to the given `FederationType` using the given name."""
        self.federation_type = federation_type
        self.name = name
        self.schema_name = self.schema_name or to_schema_name(name)

        self.ref = convert_to_federation_field_ref(self.ref, caller=self)

        if self.many is Undefined:
            self.many = is_many(self.ref, model=None, name=self.name)
        if self.nullable is Undefined:
            self.nullable = parse_is_nullable(self.ref)
        if self.description is Undefined:
            self.description = self.federation_type.__attribute_docstrings__.get(name)
            if self.description is None:
                self.description = convert_to_description(self.ref)

        for directive in self.directives:
            directive.__connected__(self)

    def __call__(self, ref: GraphQLFieldResolver, /) -> FederationField:
        """Called when using as decorator with parenthesis: @FederationField(...)"""
        self.ref = cache_signature_if_function(ref, depth=1)
        return self

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref!r})>"

    def __str__(self) -> str:
        field = self.as_graphql_field()
        return undine_settings.SDL_PRINTER.print_field(self.schema_name, field, indent=False)

    def __get__(self, instance: FederationType | None, cls: type[FederationType]) -> Any:
        if instance is None:
            return self
        try:
            return instance.__parameters__[self.name]
        except KeyError as error:
            msg = f"FederationField {self.name!r} not found on {instance!r}"
            raise ValueError(msg) from error

    def __set__(self, instance: FederationType | None, value: Any) -> None:
        if instance is None:
            msg = f"Can't set attribute {self.name!r} on {self.federation_type.__name__!r}"
            raise AttributeError(msg)
        instance.__parameters__[self.name] = value

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
        return convert_to_graphql_type(value, model=None)  # type: ignore[return-value]

    def get_field_arguments(self) -> GraphQLArgumentMap | None:
        return convert_to_graphql_argument_map(self.ref, many=self.many)

    def get_resolver(self) -> GraphQLFieldResolver:
        ref = self.resolver_func if self.resolver_func is not None else self.ref
        return convert_to_federation_field_resolver(ref, caller=self)

    def resolve(self, func: GraphQLFieldResolver | None = None, /) -> GraphQLFieldResolver:
        """
        Decorate a function to add a custom resolver for this FederationField.

        >>> class BookExt(FederationType, schema_name="Book"):
        ...     reviews = FederationField(ReviewType, many=True)
        ...
        ...     @reviews.resolve
        ...     def resolve_reviews(self, info: GQLInfo) -> list[Review]:
        ...         return Review.objects.filter(book_isbn=self.isbn)
        """
        if func is None:  # Allow `@<field_name>.resolve()`
            return self.resolve
        self.resolver_func = cache_signature_if_function(func, depth=1)
        return func

    def permissions(self, func: FederationFieldPermFunc | None = None, /) -> FederationFieldPermFunc:
        """Decorate a function to add it as a permission check for this FederationField."""
        if func is None:  # Allow `@<field_name>.permissions()`
            return self.permissions  # type: ignore[return-value]
        self.permissions_func = get_wrapped_func(func)
        return func

    def visible(self, func: VisibilityFunc | None = None, /) -> VisibilityFunc:
        """
        Decorate a function to change the FederationField's visibility in the schema.
        See the Visibility docs page for details.

        >>> @KeyDirective(fields="isbn")
        >>> class BookType(FederationType):
        ...     isbn = FederationField(str)
        ...
        ...     @isbn.visible
        ...     def isbn_visible(self: FederationField, request: DjangoRequestProtocol) -> bool:
        ...         return False
        """
        if func is None:  # Allow `@<field_name>.visible()`
            return self.visible  # type: ignore[return-value]
        self.visible_func = get_wrapped_func(func)
        return func


FEDERATION_TYPE_REGISTRY: dict[str, type[FederationType]] = {}
"""Maps of created federation types from their schema name to the class."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FederationFieldResolver:
    """Resolves a FederationField using attribute access."""

    field: FederationField

    def __call__(self, root: FederationType, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[Any]:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: FederationType, info: GQLInfo) -> Any:
        value = getattr(root, self.field.name, None)

        if value is None:
            if not self.field.nullable:
                raise GraphQLFieldNotNullableError(
                    typename=self.field.federation_type.__schema_name__,
                    field_name=self.field.schema_name,
                )
            return None

        self.check_permissions(root, info, value)
        return value

    async def run_async(self, root: FederationType, info: GQLInfo) -> Any:
        value = getattr(root, self.field.name, None)

        if value is None:
            if not self.field.nullable:
                raise GraphQLFieldNotNullableError(
                    typename=self.field.federation_type.__schema_name__,
                    field_name=self.field.schema_name,
                )
            return None

        await self.check_permissions_async(root, info, value)
        return value

    def check_permissions(self, root: FederationType, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, value)

    async def check_permissions_async(self, root: FederationType, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            if inspect.iscoroutinefunction(self.field.permissions_func):
                await self.field.permissions_func(root, info, value)
            else:
                self.field.permissions_func(root, info, value)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FederationFieldFunctionResolver:
    """Resolves a `FederationField` using the given function."""

    func: FunctionType | Callable[..., Any]
    field: FederationField

    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if undine_settings.ASYNC and inspect.iscoroutinefunction(self.func):
            return self._run_async(root, info, **kwargs)
        return self._run_sync(root, info, **kwargs)

    def _run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        self._set_kwargs(kwargs, root, info)
        value = self.func(**kwargs)
        self.check_permissions(root, info, value)
        return value

    async def _run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        self._set_kwargs(kwargs, root, info)
        value = await self.func(**kwargs)
        await self.check_permissions_async(root, info, value)
        return value

    def _set_kwargs(self, kwargs: dict[str, Any], root: Any, info: GQLInfo) -> None:
        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info

    def check_permissions(self, root: FederationType, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, value)

    async def check_permissions_async(self, root: FederationType, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            if inspect.iscoroutinefunction(self.field.permissions_func):
                await self.field.permissions_func(root, info, value)
            else:
                self.field.permissions_func(root, info, value)
