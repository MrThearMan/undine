from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models
from graphql import GraphQLResolveInfo, Undefined

from undine.metaclasses import ModelGQLFilterMeta, ModelGQLOrderingMeta, ModelGQLTypeMeta
from undine.optimizer.compiler import OptimizationCompiler
from undine.optimizer.prefetch_hack import evaluate_in_context
from undine.typing import FilterResults, OrderingResults

if TYPE_CHECKING:
    from undine.optimizer.optimizer import QueryOptimizer

__all__ = [
    "ModelGQLFilter",
    "ModelGQLOrdering",
    "ModelGQLType",
]


class ModelGQLType(metaclass=ModelGQLTypeMeta, model=Undefined):
    """
    Base class for all GraphQL Object Types backing a Django model.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this ModelGQLType represents. This input is required.
    - `filters`: Set the `ModelGQLFilter` class this ModelGQLType uses. Defaults to `None`.
    - `ordering`: Set the `ModelGQLOrdering` class this ModelGQLType uses. Defaults to `None`.
    - `exclude`: List of model fields to exclude from the automatically added fields. No excludes by default.
    - `name`: Override name for the `ModelGQLType` in the GraphQL schema. Use class name by default.
    - `register`: Whether to register the `ModelGQLType` in `TYPE_REGISTRY`. Defaults to `True`.
    - `auto_fields`: Whether to add fields for all model fields automatically. Defaults to `True`.
    - `lookup_field`: Name of the field to use for looking up single objects. Defaults to `"pk"`.
    - `extensions`: GraphQL extensions for the created ObjectType. Defaults to `None`.

    >>> class MyType(ModelGQLType, model=MyModel): ...
    """

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
    def __pre_optimization_hook__(cls, queryset: models.QuerySet, optimizer: QueryOptimizer) -> models.QuerySet:
        """
        Hook for modifying the qeuryset and optimizer data before the optimization process.
        Used to add information about required data for the model outside of the GraphQL query.
        """
        return queryset

    @classmethod
    def __is_type_of__(cls, value: models.Model, info: GraphQLResolveInfo) -> bool:
        """
        Function for resolving types of abstract GraphQL types like unions.
        Indicates whether the given value belongs to this ModelGQLType.
        """
        # Purposely not using `isinstance` here to prevent errors from model inheritance.
        return type(value) is cls.__model__


class ModelGQLFilter(metaclass=ModelGQLFilterMeta, model=Undefined):
    """
    Base class for creating filters for a `ModelGQLType`.
    Creates a single GraphQL InputObjectType from filters defined in the class,
    which can then be combined using logical operators.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `ModelGQLFilter` is for. This input is required.
               Must match the model of the `ModelGQLType` this `ModelGQLFilter` is for.
    - `auto_filters`: Whether to add filters for all model fields and their lookups automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from the automatically added filters. No excludes by default.
    - `name`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created `InputObjectType`. Defaults to `None`.

    >>> class MyFilters(ModelGQLFilter, model=MyModel): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible filter names.

    @classmethod
    def __build__(cls, filter_data: dict[str, Any], info: GraphQLResolveInfo, *, op: str = "AND") -> FilterResults:
        """
        Build a Q-object from the given filter data.
        Also indicate whether the filter should be distinct based on the fields in the filter data.

        :param filter_data: A map of filter schema names to input values.
        :param info: The GraphQL resolve info for the request.
        :param op: The logical operator to use for combining multiple filters.
        """
        q: models.Q = models.Q()
        distinct: bool = False
        aliases: dict[str, models.Expression | models.Subquery] = {}

        for filter_name, filter_value in filter_data.items():
            if filter_name in ("AND", "OR", "XOR", "NOT"):
                results = cls.__build__(filter_value, info, op=filter_name)
                filter_expression = results.q
                distinct = distinct or results.distinct
                aliases |= results.aliases

            else:
                filter_ = cls.__filter_map__[filter_name]
                distinct = distinct or filter_.distinct
                filter_expression = filter_.get_expression(filter_value, info)
                if filter_.alias_value is not None:
                    aliases[filter_.alias_name] = filter_.alias_value

            if op == "AND":
                q &= filter_expression
            elif op == "OR":
                q |= filter_expression
            elif op == "NOT":
                q = ~filter_expression
            elif op == "XOR":
                q ^= filter_expression

        return FilterResults(q=q, distinct=distinct, aliases=aliases)


class ModelGQLOrdering(metaclass=ModelGQLOrderingMeta, model=Undefined):
    """
    Base class for creating options for ordering a `ModelGQLType`.
    Creates a single GraphQL Enum from orderings defined in the class,
    which can then be combined using a list for the desired ordering.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this ModelGQLOrdering is for. This input is required.
               Must match the model of the `ModelGQLType` this `ModelGQLOrdering` is for.
    - `name`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `auto_ordering`: Whether to add ordering fields for all given model's fields automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from automatically added ordering fields. No excludes by default.
    - `extensions`: GraphQL extensions for the created GraphQLEnum. Defaults to `None`.

    >>> class MyOrdering(ModelGQLOrdering, model=MyModel): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible ordering field names.

    @classmethod
    def __build__(cls, ordering_data: list[str], info: GraphQLResolveInfo) -> OrderingResults:
        """
        Build a list of ordering expressions from the given ordering data.

        :param ordering_data: A list of ordering schema names.
        :param info: The GraphQL resolve info for the request.
        """
        result = OrderingResults(order_by=[])

        for ordering_item in ordering_data:
            if ordering_item.endswith("Desc"):
                filter_name = ordering_item[:-4]
                descending = True
            elif ordering_item.endswith("Asc"):
                filter_name = ordering_item[:-3]
                descending = False
            else:  # Does not support reversing order.
                filter_name = ordering_item
                descending = False

            ordering_ = cls.__ordering_map__[filter_name]
            result.order_by.append(ordering_.get_expression(info, descending=descending))

        return result
