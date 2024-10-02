from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import GraphQLField, GraphQLObjectType, Undefined

from undine.optimizer.compiler import OptimizationCompiler
from undine.optimizer.prefetch_hack import evaluate_in_context
from undine.utils.decorators import cached_class_method
from undine.utils.text import get_docstring

from .metaclasses.model_type_meta import ModelGQLTypeMeta

if TYPE_CHECKING:
    from django.db import models

    from undine.optimizer.optimizer import QueryOptimizer
    from undine.typing import GQLInfo, Root


__all__ = [
    "ModelGQLType",
]


class ModelGQLType(metaclass=ModelGQLTypeMeta, model=Undefined):
    """
    Base class for all GraphQL Object Types backing a Django model.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this ModelGQLType represents. This input is required.
    - `filters`: Set the `ModelGQLFilter` class this ModelGQLType uses, or `True` to create one with
                 default parameters. Defaults to `None`.
    - `ordering`: Set the `ModelGQLOrdering` class this ModelGQLType uses, or `True` to create one with
                  default parameters. Defaults to `None`.
    - `auto_fields`: Whether to add fields for all model fields automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from the automatically added fields. No excludes by default.
    - `lookup_field`: Name of the field to use for looking up single objects. Defaults to `"pk"`.
    - `name`: Override name for the `ModelGQLType` in the GraphQL schema. Use class name by default.
    - `register`: Whether to register the `ModelGQLType` in `TYPE_REGISTRY`. Defaults to `True`.
    - `extensions`: GraphQL extensions for the created ObjectType. Defaults to `None`.

    >>> class MyType(ModelGQLType, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible field names.

    @classmethod
    def __get_queryset__(cls, info: GQLInfo) -> models.QuerySet:
        """
        Base queryset for this ModelGQLType.
        Used for top-level queries and prefetches involving this ModelGQLType.
        """
        return cls.__model__._default_manager.get_queryset()

    @classmethod
    def __optimize_queryset__(cls, info: GQLInfo, queryset: models.QuerySet) -> models.QuerySet:
        """Optimize a queryset according to the given resolve info."""
        optimizer = OptimizationCompiler(info).compile(queryset)
        optimized_queryset = optimizer.optimize_queryset(queryset)
        evaluate_in_context(optimized_queryset)
        return optimized_queryset

    @classmethod
    def __filter_queryset__(cls, queryset: models.QuerySet, info: GQLInfo) -> models.QuerySet:
        """
        Filtering that should always be applied to the queryset.
        Optimizer will call this method for all querysets involving this ModelGQLType.
        """
        return queryset

    @classmethod
    def __resolve_one__(cls, root: Root, info: GQLInfo, **kwargs: Any) -> models.Model | None:
        """Top-level resolver for fetching a single model object."""
        queryset = cls.__get_queryset__(info)
        optimized_queryset = cls.__optimize_queryset__(info, queryset.filter(**kwargs))
        # Shouldn't use .first(), as it can apply additional ordering, which would cancel the optimization.
        # The queryset should have the right model instance, since we started by filtering by its pk,
        # so we can just pick that out of the result cache (if it hasn't been filtered out).
        return next(iter(optimized_queryset), None)

    @classmethod
    def __resolve_many__(cls, root: Root, info: GQLInfo, **kwargs: Any) -> models.QuerySet:
        """Top-level resolver for fetching multiple model objects."""
        queryset = cls.__get_queryset__(info)
        return cls.__optimize_queryset__(info, queryset)

    @classmethod
    def __pre_optimization_hook__(cls, queryset: models.QuerySet, optimizer: QueryOptimizer) -> models.QuerySet:
        """
        Hook for modifying the qeuryset and optimizer data before the optimization process.
        Used to add information about required data for the model outside of the GraphQL query.
        """
        return queryset

    @classmethod
    def __is_type_of__(cls, value: models.Model, info: GQLInfo) -> bool:
        """
        Function for resolving types of abstract GraphQL types like unions.
        Indicates whether the given value belongs to this ModelGQLType.
        """
        # Purposely not using `isinstance` here to prevent errors from model inheritance.
        return type(value) is cls.__model__

    @cached_class_method
    def __output_type__(cls) -> GraphQLObjectType:
        """
        Creates a `GraphQLObjectType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """

        # Defer creating fields until ModelGQLTypes have been registered.
        def fields() -> dict[str, GraphQLField]:
            return {name: field.as_graphql_field() for name, field in cls.__field_map__.items()}

        return GraphQLObjectType(
            name=cls.__typename__,
            fields=fields,
            description=get_docstring(cls),
            is_type_of=cls.__is_type_of__,
            extensions=cls.__extensions__,
        )
