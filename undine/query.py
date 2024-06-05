from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, Unpack

from graphql import DirectiveLocation, GraphQLField, Undefined

from undine.converters import (
    convert_to_description,
    convert_to_field_complexity,
    convert_to_field_ref,
    convert_to_field_resolver,
    convert_to_graphql_argument_map,
    convert_to_graphql_type,
    is_field_nullable,
    is_many,
)
from undine.dataclasses import MaybeManyOrNonNull
from undine.exceptions import MismatchingModelError, MissingModelGenericError
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type
from undine.utils.graphql.utils import check_directives
from undine.utils.model_utils import get_default_manager, get_model_fields_for_graphql
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members, get_wrapped_func
from undine.utils.registy import Registry
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Collection, Container

    from django.db.models import Model, QuerySet
    from graphql import GraphQLArgumentMap, GraphQLFieldResolver, GraphQLObjectType, GraphQLOutputType

    from undine import FilterSet, GQLInfo, InterfaceType, OrderSet
    from undine.directives import Directive
    from undine.optimizer.optimizer import OptimizationData
    from undine.typing import FieldParams, OptimizerFunc, PermissionFunc, QueryTypeParams

__all__ = [
    "Field",
    "QueryType",
]


class QueryTypeMeta(type):
    """A metaclass that modifies how a `QueryType` is created."""

    # Set in '__new__'
    __model__: type[Model]
    __filterset__: type[FilterSet] | None
    __orderset__: type[OrderSet] | None
    __field_map__: dict[str, Field]
    __schema_name__: str
    __interfaces__: Collection[type[InterfaceType]]
    __directives__: list[Directive]
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[QueryTypeParams],
    ) -> QueryTypeMeta:
        if _name == "QueryType":  # Early return for the `QueryType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        try:
            model = QueryTypeMeta.__model__
            del QueryTypeMeta.__model__
        except AttributeError as error:
            raise MissingModelGenericError(name=_name, cls="QueryType") from error

        auto = kwargs.get("auto", True)
        exclude = set(kwargs.get("exclude", []))
        if auto:
            exclude |= set(_attrs)
            _attrs |= get_fields_for_model(model, exclude=exclude)

        interfaces = kwargs.get("interfaces", [])
        for interface in interfaces:
            for field_name, interface_field in interface.__field_map__.items():
                _attrs.setdefault(field_name, interface_field.as_undine_field())

        filterset = kwargs.get("filterset")
        if filterset is not None and filterset.__model__ is not model:
            raise MismatchingModelError(
                name=filterset.__name__,
                given_model=model,
                target=_name,
                expected_model=filterset.__model__,
            )

        orderset = kwargs.get("orderset")
        if orderset is not None and orderset.__model__ is not model:
            raise MismatchingModelError(
                name=orderset.__name__,
                given_model=model,
                target=_name,
                expected_model=orderset.__model__,
            )

        query_type = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `Field` names.
        query_type.__model__ = model
        query_type.__filterset__ = filterset
        query_type.__orderset__ = orderset
        query_type.__field_map__ = get_members(query_type, Field)
        query_type.__schema_name__ = kwargs.get("schema_name", _name)
        query_type.__interfaces__ = interfaces
        query_type.__directives__ = kwargs.get("directives", [])
        query_type.__extensions__ = kwargs.get("extensions", {})
        query_type.__attribute_docstrings__ = parse_class_attribute_docstrings(query_type)

        check_directives(query_type.__directives__, location=DirectiveLocation.OBJECT)
        query_type.__extensions__[undine_settings.QUERY_TYPE_EXTENSIONS_KEY] = query_type

        for interface in interfaces:
            interface.__register_as_implementation__(query_type)  # type: ignore[arg-type]

        register = kwargs.get("register", True)
        if register:
            QUERY_TYPE_REGISTRY[model] = query_type  # type: ignore[assignment]

        for name, field in query_type.__field_map__.items():
            field.__connect__(query_type, name)  # type: ignore[arg-type]

        return query_type

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_object_type(cls.__output_type__())

    def __getitem__(cls, model: type[TModel]) -> type[QueryType[TModel]]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'QueryType'!
        QueryTypeMeta.__model__ = model
        return cls  # type: ignore[return-value]

    def __output_type__(cls) -> GraphQLObjectType:
        """Creates a GraphQL `ObjectType` for this `QueryType`."""
        return get_or_create_graphql_object_type(
            name=cls.__schema_name__,
            fields=FunctionEqualityWrapper(cls.__output_fields__, context=cls),
            interfaces=[interface.__interface__() for interface in cls.__interfaces__],
            description=get_docstring(cls),
            is_type_of=cls.__is_type_of__,
            extensions=cls.__extensions__,
        )

    def __output_fields__(cls) -> dict[str, GraphQLField]:
        """Defer creating fields until all QueryTypes have been registered."""
        return {field.schema_name: field.as_graphql_field() for field in cls.__field_map__.values()}

    def __is_type_of__(cls, value: TModel, info: GQLInfo) -> bool:
        """
        Function for resolving types of abstract GraphQL types like unions.
        Indicates whether the given value belongs to this `QueryType`.
        """
        # Purposely not using `isinstance` here since models can inherit from other models.
        return type(value) is cls.__model__


class QueryType(Generic[TModel], metaclass=QueryTypeMeta):
    """
    A class for creating a query in the GraphQL schema based on a Django Model.
    Represents a GraphQL `ObjectType` in the GraphQL schema.

    Must set the Django Model this `QueryType` is for using the Generic type parameter.

    The following parameters can be passed in the class definition:

    `filterset: type[FilterSet] = None`
        `FilterSet` class this `QueryType` uses for filtering.

    `orderset: type[OrderSet] = None`
        `OrderSet` class this `QueryType` uses for ordering.

    `auto: bool = True`
        Whether to add `Field` attributes for all Model fields automatically.

    `exclude: list[str] = []`
        Model fields to exclude from the automatically added `Field` attributes.

    `interfaces: list[type[InterfaceType]] = []`
        Interfaces this `QueryType` should implement.

    `register: bool = True`
        Whether to register the `QueryType` for the given Model.
        Only one `QueryType` can be registered per Model.
        Allows other `QueryTypes` to look up this `QueryType` for linking relations,
        and `MutationTypes` to find out their matching output type.

    `schema_name: str = <class name>`
        Override name for the `ObjectType` for the `QueryType` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `ObjectType`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `ObjectType`.

    >>> class TaskType(QueryType[Task]): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `Field` names.

    # Set in metaclass
    __model__: ClassVar[type[Model]]
    __filterset__: ClassVar[type[FilterSet] | None]
    __orderset__: ClassVar[type[OrderSet] | None]
    __field_map__: ClassVar[dict[str, Field]]
    __schema_name__: ClassVar[str]
    __interfaces__: ClassVar[Collection[type[InterfaceType]]]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        """Filtering that should always be applied when fetching objects through this QueryType."""
        return queryset

    @classmethod
    def __permissions__(cls, instance: TModel, info: GQLInfo) -> None:
        """Check permissions for accessing an instance through this `QueryType`."""

    @classmethod
    def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
        """
        Hook for modifying the optimization data outside the GraphQL resolver context.
        Can be used to e.g. optimize data for permissions checks.
        """

    @classmethod
    def __get_queryset__(cls, info: GQLInfo) -> QuerySet[TModel]:
        """Base queryset for this `QueryType`."""
        return get_default_manager(cls.__model__).get_queryset()  # type: ignore[return-value]


class Field:
    """
    A class for defining a field for a `QueryType`.
    Represents a field on a GraphQL `ObjectType` for the `QueryType` this is added to.

    >>> class TaskType(QueryType[Task]):
    ...     name = Field()
    """

    def __init__(self, ref: Any = None, **kwargs: Unpack[FieldParams]) -> None:
        """
        Create a new Field.

        :param ref: Reference to build the `Field` from. Must be convertable by the `convert_to_field_ref` function.
                    If not provided, use the name of the attribute this is assigned to in the `QueryType` class.
        :param many: Whether the `Field` should return a non-null list of the referenced type.
        :param nullable: Whether the referenced type can be null.
        :param description: Description for the `Field`.
        :param deprecation_reason: If the `Field` is deprecated, describes the reason for deprecation.
        :param complexity: The complexity of resolving this field towards the maximum complexity of an `Entrypoint`.
        :param field_name: Name of the field in the Django model. If not provided, use the name of the attribute.
        :param schema_name: Actual name of the `Field` in the GraphQL schema. Can be used to alias the `Field`
                            for the schema, or when the desired name is a Python keyword (e.g. `if` or `from`).
        :param directives: GraphQL directives for the `Field`.
        :param extensions: GraphQL extensions for the `Field`.
        """
        self.ref: Any = cache_signature_if_function(ref, depth=1)

        self.many: bool = kwargs.get("many", Undefined)  # type: ignore[assignment]
        self.nullable: bool = kwargs.get("nullable", Undefined)  # type: ignore[assignment]
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.complexity: int = kwargs.get("complexity", Undefined)  # type: ignore[assignment]
        self.field_name: str = kwargs.get("field_name", Undefined)  # type: ignore[assignment]
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})

        check_directives(self.directives, location=DirectiveLocation.FIELD_DEFINITION)
        self.extensions[undine_settings.FIELD_EXTENSIONS_KEY] = self

        self.resolver_func: GraphQLFieldResolver | None = None
        self.optimizer_func: OptimizerFunc | None = None
        self.permissions_func: PermissionFunc | None = None

    def __connect__(self, query_type: type[QueryType], name: str) -> None:
        """Connect this `Field` to the given `QueryType` using the given name."""
        self.query_type = query_type
        self.name = name
        self.field_name = self.field_name or name
        self.schema_name = self.schema_name or to_schema_name(name)

        if isinstance(self.ref, str):
            self.field_name = self.ref

        self.ref = convert_to_field_ref(self.ref, caller=self)

        if self.many is Undefined:
            self.many = is_many(self.ref, model=self.query_type.__model__, name=self.field_name)
        if self.nullable is Undefined:
            self.nullable = is_field_nullable(self.ref, caller=self)
        if self.complexity is Undefined:
            self.complexity = convert_to_field_complexity(self.ref, caller=self)
        if self.description is Undefined:
            self.description = self.query_type.__attribute_docstrings__.get(name)
            if self.description is None:
                self.description = convert_to_description(self.ref)

    def __call__(self, ref: GraphQLFieldResolver, /) -> Field:
        """Called when using as decorator with parenthesis: @Field(...)"""
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
        return convert_to_graphql_type(value, model=self.query_type.__model__)  # type: ignore[return-value]

    def get_field_arguments(self) -> GraphQLArgumentMap | None:
        return convert_to_graphql_argument_map(self.ref, many=self.many)

    def get_resolver(self) -> GraphQLFieldResolver:
        if self.resolver_func is not None:
            return convert_to_field_resolver(self.resolver_func, caller=self)
        return convert_to_field_resolver(self.ref, caller=self)

    def resolve(self, func: GraphQLFieldResolver | None = None, /) -> GraphQLFieldResolver:
        """Decorate a function to add a custom resolver for this Field."""
        if func is None:  # Allow `@<field_name>.resolve()`
            return self.resolve
        self.resolver_func = cache_signature_if_function(func, depth=1)
        return func

    def optimize(self, func: OptimizerFunc | None = None, /) -> OptimizerFunc:
        """Decorate a function to add custom optimization rules for this Field."""
        if func is None:  # Allow `@<field_name>.optimize()`
            return self.optimize  # type: ignore[return-value]
        self.optimizer_func = get_wrapped_func(func)
        return func

    def permissions(self, func: PermissionFunc | None = None, /) -> PermissionFunc:
        """Decorate a function to add it as a permission check for this field."""
        if func is None:  # Allow `@<field_name>.permissions()`
            return self.permissions  # type: ignore[return-value]
        self.permissions_func = get_wrapped_func(func)
        return func


def get_fields_for_model(model: type[Model], *, exclude: Container[str] = ()) -> dict[str, Field]:
    """Add undine.Fields for all the given model's fields, except those in the 'exclude' list."""
    result: dict[str, Field] = {}

    for model_field in get_model_fields_for_graphql(model):
        field_name = model_field.name

        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        result[field_name] = Field(model_field)

    return result


QUERY_TYPE_REGISTRY: Registry[type[Model], type[QueryType]] = Registry()
"""
Maps from a Django Model class to a corresponding `QueryType`.
This allows deferring the creation of field resolvers for related fields,
which would use a `QueryType` that is not created when the field is defined.
"""
