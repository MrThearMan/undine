from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from django.db.models import F
from graphql import (
    GraphQLArgumentMap,
    GraphQLField,
    GraphQLFieldResolver,
    GraphQLInterfaceType,
    GraphQLOutputType,
    Undefined,
)

from undine.converters import (
    convert_field_ref_to_resolver,
    convert_to_field_ref,
    convert_to_graphql_argument_map,
    convert_to_graphql_type,
    is_field_nullable,
    is_many,
)
from undine.errors.exceptions import MismatchingModelError, MissingModelError
from undine.middleware.query import QueryPermissionCheckMiddleware
from undine.parsers import parse_class_variable_docstrings, parse_description
from undine.registies import QUERY_TYPE_REGISTRY
from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_object_type, maybe_list_or_non_null
from undine.utils.model_utils import get_model_fields_for_graphql
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members, get_wrapped_func
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Collection, Container, Iterable
    from types import FunctionType

    from django.db.models import Model, QuerySet

    from undine import FilterSet, OrderSet
    from undine.middleware.query import QueryMiddleware
    from undine.optimizer.optimizer import OptimizationData
    from undine.typing import CalculationResolver, FieldPermFunc, GQLInfo, OptimizerFunc, Self

__all__ = [
    "Field",
    "QueryType",
]


class QueryTypeMeta(type):
    """A metaclass that modifies how a `QueryType` is created."""

    def __new__(  # noqa: PLR0913
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        *,
        # See `QueryType` for documentation of arguments.
        model: type[Model] | None = None,
        filterset: type[FilterSet] | Literal[True] | None = None,
        orderset: type[OrderSet] | Literal[True] | None = None,
        auto: bool = True,
        exclude: Iterable[str] = (),
        max_complexity: int | None = Undefined,
        interfaces: Collection[GraphQLInterfaceType] = (),
        typename: str | None = None,
        register: bool = True,
        extensions: dict[str, Any] | None = None,
    ) -> QueryTypeMeta:
        if model is Undefined:  # Early return for the `QueryType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="QueryType")

        if auto:
            _attrs |= get_fields_for_model(model, exclude=set(exclude) | set(_attrs))

        for interface in interfaces:
            for field_name, field in interface.fields.items():
                interface_field = Field(field.type)
                interface_field.resolver_func = field.resolve
                _attrs.setdefault(field_name, interface_field)

        if filterset is True:
            from undine import FilterSet  # noqa: PLC0415

            class_name = model.__name__ + FilterSet.__name__
            filterset = type(class_name, (FilterSet,), {}, model=model)

        if filterset is not None and filterset.__model__ is not model:
            raise MismatchingModelError(
                cls=filterset.__name__,
                given_model=model,
                type=_name,
                expected_model=filterset.__model__,
            )

        if orderset is True:
            from undine import OrderSet  # noqa: PLC0415

            class_name = model.__name__ + OrderSet.__name__
            orderset = type(class_name, (OrderSet,), {}, model=model)

        if orderset is not None and orderset.__model__ is not model:
            raise MismatchingModelError(
                cls=orderset.__name__,
                given_model=model,
                type=_name,
                expected_model=orderset.__model__,
            )

        # Add to attrs things that need to be available during `Field.__set_name__`.
        _attrs["__model__"] = model
        instance: type[QueryType] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        if register:
            QUERY_TYPE_REGISTRY[model] = instance

        if max_complexity is Undefined:
            max_complexity = undine_settings.OPTIMIZER_MAX_COMPLEXITY

        # Members should use `__dunder__` names to avoid name collisions with possible `undine.Field` names.
        instance.__model__ = model
        instance.__filterset__ = filterset
        instance.__orderset__ = orderset
        instance.__max_complexity__ = max_complexity
        instance.__field_map__ = dict(get_members(instance, Field))
        instance.__typename__ = typename or _name
        instance.__interfaces__ = interfaces
        instance.__extensions__ = (extensions or {}) | {undine_settings.QUERY_TYPE_EXTENSIONS_KEY: instance}
        return instance


class QueryType(metaclass=QueryTypeMeta, model=Undefined):
    """
    A class representing a GraphQL Object Type for a Query based on a Django Model.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `QueryType` represents. This input is required.
    - `filterset`: Set the `FilterSet` class this QueryType uses, or `True` to create one with
                   default parameters. Defaults to `None`.
    - `orderset`: Set the `OrderSet` class this QueryType uses, or `True` to create one with
                  default parameters. Defaults to `None`.
    - `auto`: Whether to add fields for all model fields automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from the automatically added fields. No excludes by default.
    - `max_complexity`: Maximum number of relations allowed in a query when using this QueryType as the Entrypoint.
                        Use value of `OPTIMIZER_MAX_COMPLEXITY` setting by default.
    - `interfaces`: List of interfaces to use for this QueryType. Defaults to an empty tuple.
    - `typename`: Override name for the `QueryType` in the GraphQL schema. Use class name by default.
    - `register`: Whether to register the `QueryType` for the given model so that other `QueryTypes` can use it in
                 their fields and `MutationTypes` can use it as their output type. Defaults to `True`.
    - `extensions`: GraphQL extensions for the created ObjectType. Defaults to `None`.

    >>> class MyQueryType(QueryType, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `undine.Field` names.

    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        """Filtering that should always be applied when fetching objects through this QueryType."""
        return queryset

    @classmethod
    def __permissions_single__(cls, instance: Model, info: GQLInfo) -> None:
        """Check permissions for accessing the given instance through this QueryType."""

    @classmethod
    def __permissions_many__(cls, instances: list[Model], info: GQLInfo) -> None:
        """Check permissions for accessing the given instances through this QueryType."""

    @classmethod
    def __optimizer_hook__(cls, data: OptimizationData, info: GQLInfo) -> None:
        """
        Hook for modifying the optimization data outside the GraphQL resolver context.
        Can be used to optimize e.g. data for permissions checks.
        """

    @classmethod
    def __get_queryset__(cls, info: GQLInfo) -> QuerySet:
        """Base queryset for this QueryType."""
        return cls.__model__._default_manager.get_queryset()

    @classmethod
    def __is_type_of__(cls, value: Model, info: GQLInfo) -> bool:
        """
        Function for resolving types of abstract GraphQL types like unions.
        Indicates whether the given value belongs to this QueryType.
        """
        # Purposely not using `isinstance` here to prevent errors from model inheritance.
        return type(value) is cls.__model__

    @classmethod
    def __output_type__(cls) -> GraphQLOutputType:
        """Creates a `GraphQLObjectType` for this QueryType to use in the GraphQL schema."""

        # Defer creating fields until all QueryTypes have been registered.
        def fields() -> dict[str, GraphQLField]:
            return {to_schema_name(name): field.as_graphql_field() for name, field in cls.__field_map__.items()}

        return get_or_create_object_type(
            name=cls.__typename__,
            fields=FunctionEqualityWrapper(fields, context=cls),
            interfaces=cls.__interfaces__,
            description=get_docstring(cls),
            is_type_of=cls.__is_type_of__,
            extensions=cls.__extensions__,
        )

    @classmethod
    def __middleware__(cls) -> list[type[QueryMiddleware]]:
        """Middleware to use with queries using this QueryType."""
        return [
            QueryPermissionCheckMiddleware,
        ]


class Field:
    """
    A class representing a queryable field on a GraphQL Object Type.
    Can be added to the class body of a `QueryType` class.
    """

    def __init__(
        self,
        ref: Any = None,
        *,
        many: bool = Undefined,
        nullable: bool = Undefined,
        description: str | None = Undefined,
        field_name: str | None = None,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        Create a new Field.

        :param ref: Reference to build the Field from. Can be anything that `convert_to_field_ref` can convert,
                    e.g., a string referencing a Model Field name, a Model Field, an expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `QueryType` class.
        :param many: Whether the Field should contain a non-null list of the referenced type.
                     If not provided, looks at the reference and tries to determine this from it.
        :param nullable: Whether the referenced type can be null. If not provided, looks at the converted
                         reference and tries to determine nullability from it.
        :param description: Description for the Field. If not provided, looks at the converted reference
                            and tries to find the description from it.
        :param field_name: Name of the Model Field this Field is for. Use this if the Field's name in the
                           `QueryType` class is different from the Model Field name. Not required if `ref` is
                           a string referencing a Model Field name.
        :param deprecation_reason: If the Field is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the Field.
        """
        self.ref = cache_signature_if_function(ref, depth=1)
        self.many = many
        self.nullable = nullable
        self.description = description
        self.field_name = field_name
        self.deprecation_reason = deprecation_reason
        self.resolver_func: GraphQLFieldResolver | None = None
        self.optimizer_func: OptimizerFunc | None = None
        self.permissions_func: FieldPermFunc | None = None
        self.calculate_func: CalculationResolver | None = None
        self.skip_query_type_perms: bool = False
        self.extensions: dict[str, Any] = extensions or {}
        self.extensions[undine_settings.FIELD_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[QueryType], name: str) -> None:
        self.query_type = owner
        self.name = name

        if self.field_name is None:
            self.field_name = self.name
            if isinstance(self.ref, str) and self.ref != "self":
                self.field_name = self.ref
            elif isinstance(self.ref, F):
                self.field_name = self.ref.name

        self.ref = convert_to_field_ref(self.ref, caller=self)

        if self.many is Undefined:
            self.many = is_many(self.ref, model=self.query_type.__model__, name=self.field_name)
        if self.nullable is Undefined:
            self.nullable = is_field_nullable(self.ref, caller=self)
        if self.description is Undefined:
            variable_docstrings = parse_class_variable_docstrings(self.query_type)
            self.description = variable_docstrings.get(self.name, Undefined)
            if self.description is Undefined:
                self.description = parse_description(self.ref)

    def __call__(self, ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Field(...)"""
        self.ref = cache_signature_if_function(ref, depth=1)
        return self

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref})>"

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
        graphql_type = convert_to_graphql_type(self.ref, model=self.query_type.__model__)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=not self.nullable)

    def get_field_arguments(self) -> GraphQLArgumentMap:
        return convert_to_graphql_argument_map(self.ref, many=self.many)

    def get_resolver(self) -> GraphQLFieldResolver:
        if self.resolver_func is not None:
            return convert_field_ref_to_resolver(self.resolver_func, caller=self)
        return convert_field_ref_to_resolver(self.ref, caller=self)

    def resolve(self, func: GraphQLFieldResolver = None, /) -> GraphQLFieldResolver:
        """Decorate a function to add a custom resolver for this Field."""
        if func is None:  # Allow `@<field_name>.resolve()`
            return self.resolve  # type: ignore[return-value]
        self.resolver_func = cache_signature_if_function(func, depth=1)
        return func

    def optimize(self, func: OptimizerFunc = None, /) -> OptimizerFunc:
        """Decorate a function to add custom optimization rules for this Field."""
        if func is None:  # Allow `@<field_name>.optimize()`
            return self.optimize  # type: ignore[return-value]
        self.optimizer_func = get_wrapped_func(func)
        return func

    def permissions(self, func: FieldPermFunc = None, /, *, skip_query_type_perms: bool = False) -> FieldPermFunc:
        """
        Decorate a function to add it as a permission check for this field.

        :param skip_query_type_perms: Whether to skip QueryType's permissions checks for this field.
                                      for this field. Only affects fields referencing another QueryType.
        """
        if func is None:  # Allow `@<field_name>.permissions()`
            self.skip_query_type_perms = skip_query_type_perms
            return self.permissions  # type: ignore[return-value]
        self.permissions_func = get_wrapped_func(func)
        return func

    def calculate(self, func: CalculationResolver, /) -> CalculationResolver:
        """Decorate a function to modify the queryset when this Field is queried."""
        if func is None:  # Allow `@<field_name>.calculate()`
            return self.calculate  # type: ignore[return-value]
        self.calculate_func = get_wrapped_func(func)
        return func


def get_fields_for_model(model: type[Model], *, exclude: Container[str]) -> dict[str, Field]:  # TODO: Test
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
