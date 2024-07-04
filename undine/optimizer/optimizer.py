from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Literal

from django.db.models import Model, Prefetch, QuerySet
from django.db.models.constants import LOOKUP_SEP

from undine.settings import undine_settings
from undine.utils.reflection import swappable_by_subclassing

from .filter_info import get_filter_info

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo

    from undine.typing import ExpressionKind, GraphQLFilterInfo, QuerySetResolver

__all__ = [
    "QueryOptimizer",
]


@dataclasses.dataclass
class OptimizationResults:
    name: str | None = None
    queryset: QuerySet | None = None
    only_fields: list[str] = dataclasses.field(default_factory=list)
    related_fields: list[str] = dataclasses.field(default_factory=list)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[Prefetch | str] = dataclasses.field(default_factory=list)

    def __add__(self, other: OptimizationResults) -> OptimizationResults:
        """Adding two compilation results together means extending the lookups to the other model."""
        self.select_related.append(other.name)
        self.only_fields.extend(f"{other.name}{LOOKUP_SEP}{only}" for only in other.only_fields)
        self.related_fields.extend(f"{other.name}{LOOKUP_SEP}{only}" for only in other.related_fields)
        self.select_related.extend(f"{other.name}{LOOKUP_SEP}{select}" for select in other.select_related)

        for prefetch in other.prefetch_related:
            if isinstance(prefetch, str):
                self.prefetch_related.append(f"{other.name}{LOOKUP_SEP}{prefetch}")
            if isinstance(prefetch, Prefetch):
                prefetch.add_prefix(other.name)
                self.prefetch_related.append(prefetch)

        return self


@swappable_by_subclassing
class QueryOptimizer:
    """Creates optimized queryset based on the optimization data found by the OptimizationCompiler."""

    def __init__(
        self,
        model: type[Model] | None,
        info: GraphQLResolveInfo,
        name: str | None = None,
        parent: QueryOptimizer | None = None,
    ) -> None:
        self.model = model
        self.info = info
        self.name = name
        self.parent = parent

        self.only_fields: list[str] = []
        self.related_fields: list[str] = []
        self.aliases: dict[str, ExpressionKind] = {}
        self.annotations: dict[str, ExpressionKind] = {}
        self.select_related: dict[str, QueryOptimizer] = {}
        self.prefetch_related: dict[str, QueryOptimizer] = {}
        self.manual_optimizers: dict[str, QuerySetResolver] = {}

    def optimize_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Add the optimizations in this optimizer to the given queryset.

        :param queryset: QuerySet to optimize.
        """
        filter_info = get_filter_info(self.info, queryset.model)
        results = self.process(queryset, filter_info)
        return self.optimize(results, filter_info)

    def pre_processing(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> QuerySet:
        """Run all pre-optimization hooks on the objct type mathcing the queryset's model."""
        return filter_info.model_type.__pre_optimization_hook__(queryset, self)

    def process(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> OptimizationResults:
        """Process compiled optimizations to optimize the given queryset."""
        queryset = self.pre_processing(queryset, filter_info)
        queryset = self.run_manual_optimizers(queryset, filter_info)

        results = OptimizationResults(
            name=self.name,
            queryset=queryset,
            only_fields=self.only_fields,
            related_fields=self.related_fields,
        )

        for name, optimizer in self.select_related.items():
            nested_filter_info = filter_info.children[name]
            queryset = nested_filter_info.model_type.__get_queryset__(self.info)
            nested_results = optimizer.process(queryset, nested_filter_info)

            # Promote `select_related` to `prefetch_related` if any annotations are needed.
            if optimizer.annotations:
                prefetch = optimizer.process_prefetch(name, nested_results, nested_filter_info)
                results.prefetch_related.append(prefetch)
                continue

            # Otherwise extend lookups to this model.
            results += nested_results

        for name, optimizer in self.prefetch_related.items():
            # For generic foreign keys, we don't know the model, so we can't optimize the queryset.
            if optimizer.model is None:
                results.prefetch_related.append(optimizer.name)
                continue

            nested_filter_info = filter_info.children[name]
            queryset = nested_filter_info.model_type.__get_queryset__(self.info)
            nested_results = optimizer.process(queryset, nested_filter_info)

            prefetch = optimizer.process_prefetch(name, nested_results, nested_filter_info)
            results.prefetch_related.append(prefetch)

        return results

    def optimize(self, results: OptimizationResults, filter_info: GraphQLFilterInfo) -> QuerySet:
        """Optimize the given queryset based on the optimization results."""
        queryset = results.queryset

        if results.select_related:
            queryset = queryset.select_related(*results.select_related)
        if results.prefetch_related:
            queryset = queryset.prefetch_related(*results.prefetch_related)
        if not undine_settings.DISABLE_ONLY_FIELDS_OPTIMIZATION and (results.only_fields or results.related_fields):
            queryset = queryset.only(*results.only_fields, *results.related_fields)
        if self.aliases or filter_info.aliases:
            queryset = queryset.alias(**self.aliases, **filter_info.aliases)
        if self.annotations:
            queryset = queryset.annotate(**self.annotations)

        return self.filter_queryset(queryset, filter_info)

    def process_prefetch(self, to_attr: str, results: OptimizationResults, filter_info: GraphQLFilterInfo) -> Prefetch:
        """Process a prefetch, optimizing its queryset based on the given filter info."""
        queryset = self.optimize(results, filter_info)
        return Prefetch(self.name, queryset, to_attr=to_attr if to_attr != self.name else None)

    def filter_queryset(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> QuerySet:
        queryset = filter_info.model_type.__filter_queryset__(queryset, self.info)
        if filter_info.order_by:
            queryset = queryset.order_by(*filter_info.order_by)
        if filter_info.filters:
            queryset = queryset.filter(filter_info.filters)
            if filter_info.distinct:
                queryset = queryset.distinct()
        return queryset

    def run_manual_optimizers(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> QuerySet:
        for name, func in self.manual_optimizers.items():
            # TODO: Refactor this.
            nested_filter_info: GraphQLFilterInfo | None = filter_info.children.get(name)
            filters = nested_filter_info.filters if nested_filter_info is not None else {}
            queryset = func(queryset, self, filters)
        return queryset

    def has_child_optimizer(self, name: str) -> bool:  # pragma: no cover
        return name in self.select_related or name in self.prefetch_related

    def get_child_optimizer(self, name: str) -> QueryOptimizer | None:  # pragma: no cover
        return self.select_related.get(name) or self.prefetch_related.get(name)

    def get_or_set_child_optimizer(  # pragma: no cover
        self,
        name: str,
        optimizer: QueryOptimizer,
        *,
        set_as: Literal["select_related", "prefetch_related"] = "select_related",
    ) -> QueryOptimizer:
        maybe_optimizer = self.select_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer
        maybe_optimizer = self.prefetch_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer
        getattr(self, set_as)[name] = optimizer
        return optimizer
