from __future__ import annotations

from dataclasses import dataclass
from inspect import cleandoc
from typing import TYPE_CHECKING, Any, Callable

from graphql import GraphQLObjectType, GraphQLResolveInfo, Undefined

from undine.fields import get_fields_from_class
from undine.metaclasses import ModelGQLTypeMeta
from undine.optimizer.compiler import OptimizationCompiler
from undine.optimizer.prefetch_hack import evaluate_in_context
from undine.settings import undine_settings
from undine.utils import dotpath

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
    from django.db import models

    from undine.optimizer.optimizer import QueryOptimizer
    from undine.typing import ToManyField, ToOneField

__all__ = [
    "ModelGQLType",
]


class ModelGQLType(metaclass=ModelGQLTypeMeta, model=Undefined):
    """Base class for all GraphQL nodes backing a Django model."""

    # Members should use `__dunder__` names to avoid name collisions with possible field names.

    @classmethod
    def __get_queryset__(cls, info: GraphQLResolveInfo) -> models.QuerySet:
        """
        Base queryset for this ModelGQLType.
        Used for top-level queries and prefetches involving this ModelGQLType.
        """
        return cls.__model__._default_manager.get_queryset()

    @classmethod
    def __optimize_queryset__(cls, info: GraphQLResolveInfo, queryset: models.QuerySet) -> models.QuerySet:
        """Optimize a queryset according to the given resolve info."""
        optimizer = OptimizationCompiler(info).compile(queryset)
        optimized_queryset = optimizer.optimize_queryset(queryset)
        evaluate_in_context(optimized_queryset)
        return optimized_queryset

    @classmethod
    def __filter_queryset__(cls, queryset: models.QuerySet, info: GraphQLResolveInfo) -> models.QuerySet:
        """
        Filtering that should always be applied to the queryset.
        Optimizer will call this method for all querysets involving this ModelGQLType.
        """
        return queryset

    @classmethod
    def __resolve_one__(cls, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> models.Model | None:
        """Top-level resolver for fetching a single model object."""
        queryset = cls.__get_queryset__(info)
        optimized_queryset = cls.__optimize_queryset__(info, queryset.filter(**kwargs))
        # Shouldn't use .first(), as it can apply additional ordering, which would cancel the optimization.
        # The queryset should have the right model instance, since we started by filtering by its pk,
        # so we can just pick that out of the result cache (if it hasn't been filtered out).
        return next(iter(optimized_queryset), None)

    @classmethod
    def __resolve_many__(cls, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> models.QuerySet:
        """Top-level resolver for fetching multiple model objects."""
        queryset = cls.__get_queryset__(info)
        return cls.__optimize_queryset__(info, queryset)

    @classmethod
    def __get_object_type__(cls) -> GraphQLObjectType:
        # Cache created type so that multiple fields can reuse it.
        # GraphQL schema cannot contain multiple types with the same name.
        if not hasattr(cls, "__object_type__"):
            cls.__object_type__ = GraphQLObjectType(
                name=cls.__graphql_name__,
                # Give fields as a callable to delay their creation.
                # This gives time for all ModelGQLTypes to be registered.
                fields=lambda: get_fields_from_class(cls),
                description=cleandoc(cls.__doc__ or "").strip(),
                is_type_of=None,  # TODO: Implement?
                extensions={
                    undine_settings.MODEL_TYPE_EXTENSIONS_KEY: cls,
                },
            )
        return cls.__object_type__

    @classmethod
    def __pre_optimization_hook__(cls, queryset: models.QuerySet, optimizer: QueryOptimizer) -> models.QuerySet:
        """
        Hook for modifying the qeuryset and optimizer data before the optimization process.
        Used to add information about required data for the model outside of the GraphQL query.
        """
        return queryset


@dataclass
class DeferredModelGQLType:
    """Represents a lazily evaluated ModelGQLType for a related field."""

    get_type: Callable[[], type[ModelGQLType]]
    name: str
    description: str | None
    nullable: bool
    many: bool
    model: type[models.Model]

    @classmethod
    def for_related_field(cls, field: ToOneField | ToManyField | GenericRelation | GenericRel) -> DeferredModelGQLType:
        name = field.name
        description = getattr(field, "help_text", None)
        nullable = field.null is True
        many = bool(field.many_to_many or field.one_to_many)
        model = field.related_model

        def inner() -> type[ModelGQLType]:
            value = ModelGQLTypeMeta.type_registry.get(model)
            if value is None:
                msg = f"ModelGQLType for field '{name}' of type '{dotpath(model)}' does not exist."
                raise ValueError(msg)

            return value

        return cls(get_type=inner, name=name, description=description, nullable=nullable, many=many, model=model)


@dataclass
class DeferredModelGQLTypeUnion:
    """Represents a lazily evaluated ModelGQLType for a related field."""

    get_types: Callable[[], list[type[ModelGQLType]]]
    name: str
    description: str | None
    model: type[models.Model]

    @classmethod
    def for_generic_foreign_key(cls, field: GenericForeignKey) -> DeferredModelGQLTypeUnion:
        from django.contrib.contenttypes.fields import GenericRelation

        name = field.name
        model = field.model
        deferred_types = [
            DeferredModelGQLType.for_related_field(f.remote_field)
            for f in model._meta._relation_tree  # noqa: SLF001
            if isinstance(f, GenericRelation)
        ]

        def inner() -> list[type[ModelGQLType]]:
            nonlocal deferred_types
            return [deferred_type.get_type() for deferred_type in deferred_types]

        return cls(get_types=inner, name=name, description="", model=model)
