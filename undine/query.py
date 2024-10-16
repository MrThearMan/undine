"""Contains code for creating Query ObjectTypes for a GraphQL schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Container, Iterable, Literal

from graphql import (
    GraphQLArgumentMap,
    GraphQLField,
    GraphQLFieldResolver,
    GraphQLObjectType,
    GraphQLOutputType,
    Undefined,
)

from undine.converters import (
    convert_field_ref_to_graphql_argument_map,
    convert_field_ref_to_resolver,
    convert_ref_to_graphql_output_type,
    convert_to_description,
    convert_to_field_ref,
    is_field_nullable,
    is_many,
)
from undine.errors.exceptions import MismatchingModelError, MissingModelError
from undine.optimizer.compiler import OptimizationCompiler
from undine.optimizer.prefetch_hack import evaluate_in_context
from undine.registies import QUERY_TYPE_REGISTRY
from undine.settings import undine_settings
from undine.utils.decorators import cached_class_method
from undine.utils.graphql import maybe_list_or_non_null
from undine.utils.model_utils import get_lookup_field_name
from undine.utils.reflection import cache_signature_if_function, get_members
from undine.utils.text import dotpath, get_docstring, get_schema_name

if TYPE_CHECKING:
    from types import FunctionType

    from django.db import models

    from undine import FilterSet, OrderSet
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.typing import GQLInfo, Root, Self

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
        model: type[models.Model] | None = None,
        filterset: type[FilterSet] | Literal[True] | None = None,
        orderset: type[OrderSet] | Literal[True] | None = None,
        auto: bool = True,
        exclude: Iterable[str] = (),
        lookup_field: str = "pk",
        typename: str | None = None,
        register: bool = True,
        extensions: dict[str, Any] | None = None,
    ) -> QueryTypeMeta:
        """See `QueryType` for documentation of arguments."""
        if model is Undefined:  # Early return for the `QueryType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="QueryType")

        if auto:
            _attrs |= get_fields_for_model(model, exclude=set(exclude) | set(_attrs))

        if filterset is True:
            from undine import FilterSet

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
            from undine import OrderSet

            class_name = model.__name__ + OrderSet.__name__
            orderset = type(class_name, (OrderSet,), {}, model=model)

        if orderset is not None and orderset.__model__ is not model:
            raise MismatchingModelError(
                cls=orderset.__name__,
                given_model=model,
                type=_name,
                expected_model=orderset.__model__,
            )

        # Add model to attrs before class creation so that it's available during `Field.__set_name__`.
        _attrs["__model__"] = model
        instance: type[QueryType] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        if register:
            QUERY_TYPE_REGISTRY[model] = instance

        # Members should use `__dunder__` names to avoid name collisions with possible `undine.Field` names.
        instance.__model__ = model
        instance.__filterset__ = filterset
        instance.__orderset__ = orderset
        instance.__lookup_field__ = lookup_field
        instance.__field_map__ = {get_schema_name(name): field for name, field in get_members(instance, Field)}
        instance.__typename__ = typename or _name
        instance.__extensions__ = (extensions or {}) | {undine_settings.QUERY_TYPE_EXTENSIONS_KEY: instance}
        return instance


class QueryType(metaclass=QueryTypeMeta, model=Undefined):
    """
    A class for creating a 'GraphQLObjectType' for a Django model.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `QueryType` represents. This input is required.
    - `filterset`: Set the `FilterSet` class this QueryType uses, or `True` to create one with
                   default parameters. Defaults to `None`.
    - `orderset`: Set the `OrderSet` class this QueryType uses, or `True` to create one with
                  default parameters. Defaults to `None`.
    - `auto`: Whether to add fields for all model fields automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from the automatically added fields. No excludes by default.
    - `lookup_field`: Name of the field to use for looking up single objects. Defaults to `"pk"`.
    - `typename`: Override name for the `QueryType` in the GraphQL schema. Use class name by default.
    - `register`: Whether to register the `QueryType` for the given model so that other `QueryTypes` can use it in
                 their fields and `MutationTypes` can use it as their output type. Defaults to `True`.
    - `extensions`: GraphQL extensions for the created ObjectType. Defaults to `None`.

    >>> class MyQueryType(QueryType, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `undine.Field` names.

    @classmethod
    def __get_queryset__(cls, info: GQLInfo) -> models.QuerySet:
        """
        Base queryset for this QueryType.
        Used for top-level queries and prefetches involving this QueryType.
        """
        return cls.__model__._default_manager.get_queryset()

    @classmethod
    def __optimize_queryset__(cls, queryset: models.QuerySet, info: GQLInfo) -> models.QuerySet:
        """Optimize a queryset according to the given resolve info."""
        optimizer = OptimizationCompiler(info).compile(queryset)
        optimized_queryset = optimizer.optimize_queryset(queryset)
        evaluate_in_context(optimized_queryset)
        return optimized_queryset

    @classmethod
    def __filter_queryset__(cls, queryset: models.QuerySet, info: GQLInfo) -> models.QuerySet:
        """
        Filtering that should always be applied to the queryset.
        Optimizer will call this method for all querysets involving this QueryType.
        """
        return queryset

    @classmethod
    def __resolve_one__(cls, root: Root, info: GQLInfo, **kwargs: Any) -> models.Model | None:
        """Top-level resolver for fetching a single model object."""
        queryset = cls.__get_queryset__(info)
        optimized_queryset = cls.__optimize_queryset__(queryset.filter(**kwargs), info)
        # Shouldn't use .first(), as it can apply additional ordering, which would cancel the optimization.
        # The queryset should have the right model instance, since we started by filtering by its pk,
        # so we can just pick that out of the result cache (if it hasn't been filtered out).
        return next(iter(optimized_queryset), None)

    @classmethod
    def __resolve_many__(cls, root: Root, info: GQLInfo, **kwargs: Any) -> models.QuerySet:
        """Top-level resolver for fetching multiple model objects."""
        queryset = cls.__get_queryset__(info)
        return cls.__optimize_queryset__(queryset, info)

    @classmethod
    def __pre_optimization_hook__(cls, queryset: models.QuerySet, optimizer: QueryOptimizer) -> models.QuerySet:
        """
        Hook for modifying the queryset and optimizer data before the optimization process.
        Used to add information about required data for the model outside of the GraphQL query.
        """
        return queryset

    @classmethod
    def __is_type_of__(cls, value: models.Model, info: GQLInfo) -> bool:
        """
        Function for resolving types of abstract GraphQL types like unions.
        Indicates whether the given value belongs to this QueryType.
        """
        # Purposely not using `isinstance` here to prevent errors from model inheritance.
        return type(value) is cls.__model__

    @cached_class_method
    def __output_type__(cls) -> GraphQLObjectType:
        """
        Creates a `GraphQLObjectType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """

        # Defer creating fields until QueryTypes have been registered.
        def fields() -> dict[str, GraphQLField]:
            return {name: field.as_graphql_field() for name, field in cls.__field_map__.items()}

        return GraphQLObjectType(
            name=cls.__typename__,
            fields=fields,
            description=get_docstring(cls),
            is_type_of=cls.__is_type_of__,
            extensions=cls.__extensions__,
        )


class Field:
    def __init__(
        self,
        ref: Any = None,
        *,
        many: bool = Undefined,
        nullable: bool = Undefined,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a `GraphQLField` in the `GraphQLObjectType` of a `QueryType`.
        In other words, it's a field that can be queried from the `QueryType` it belongs to.

        :param ref: Reference to build the field from. Can be anything that `convert_to_field_ref` can convert,
                    e.g., a string referencing a model field name, a model field, an expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `QueryType` class.
        :param many: Whether the field should contain a non-null list of the referenced type.
                     If not provided, looks at the reference and tries to determine this from it.
        :param nullable: Whether the referenced type can be null. If not provided, looks at the converted
                         reference and tries to determine nullability from it.
        :param description: Description for the field. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the field is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the field.
        """
        self.ref = cache_signature_if_function(ref, depth=1)
        self.many = many
        self.nullable = nullable
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions: dict[str, Any] = extensions or {}
        self.extensions[undine_settings.FIELD_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type | type[QueryType], name: str) -> None:
        self.owner = owner
        self.name = name
        self.ref = convert_to_field_ref(self.ref, caller=self)

        if self.many is Undefined:
            self.many = is_many(self.ref, model=self.owner.__model__, name=self.name)
        if self.nullable is Undefined:
            self.nullable = is_field_nullable(self.ref)
        if self.description is Undefined:
            self.description = convert_to_description(self.ref)

    def __call__(self, ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Field()"""
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
        graphql_type = convert_ref_to_graphql_output_type(self.ref)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=not self.nullable)

    def get_field_arguments(self) -> GraphQLArgumentMap:
        return convert_field_ref_to_graphql_argument_map(self.ref, many=self.many)

    def get_resolver(self) -> GraphQLFieldResolver:
        return convert_field_ref_to_resolver(self.ref, many=self.many, name=self.name)

    def optimizer_hook(self, optimizer: QueryOptimizer) -> None:
        """Hook for customizing how the field is optimized by the QueryOptimizer."""


def get_fields_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Field]:
    """Add undine.Fields for all of the given model's fields, except those in the 'exclude' list."""
    result: dict[str, Field] = {}
    for model_field in model._meta._get_fields():
        field_name = model_field.name
        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if is_primary_key:
            field_name = get_lookup_field_name(model)

        if field_name in exclude:
            continue

        result[field_name] = Field(model_field)

    return result
