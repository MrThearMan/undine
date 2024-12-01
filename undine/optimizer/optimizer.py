from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Model, Prefetch, QuerySet

from undine.dataclasses import GraphQLFilterInfo, OptimizationResults
from undine.settings import undine_settings
from undine.utils.reflection import swappable_by_subclassing

from .filter_info import get_filter_info

if TYPE_CHECKING:
    from undine.typing import ExpressionLike, GQLInfo

__all__ = [
    "QueryOptimizer",
]


@swappable_by_subclassing
class QueryOptimizer:
    """Creates optimized queryset based on the optimization data found by the OptimizationCompiler."""

    def __init__(
        self,
        model: type[Model] | None,
        info: GQLInfo,
        name: str | None = None,
        parent: QueryOptimizer | None = None,
    ) -> None:
        self.model = model
        self.info = info
        self.name = name
        self.parent = parent

        self.only_fields: list[str] = []
        self.related_fields: list[str] = []
        self.aliases: dict[str, ExpressionLike] = {}
        self.annotations: dict[str, ExpressionLike] = {}
        self.select_related: dict[str, QueryOptimizer] = {}
        self.prefetch_related: dict[str, QueryOptimizer] = {}

    def optimize_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Add the optimizations in this optimizer to the given queryset.

        :param queryset: QuerySet to optimize.
        """
        filter_info = get_filter_info(self.info, queryset.model)
        results = self.process(queryset, filter_info)
        return self.optimize(results, filter_info)

    def process(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> OptimizationResults:
        """Process compiled optimizations to optimize the given queryset."""
        filter_info.model_type.__optimizer_hook__(self)

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
        for ftr in filter_info.filters:
            queryset = queryset.filter(ftr)
        if filter_info.distinct:
            queryset = queryset.distinct()
        return queryset

    def add_select_related(self, name: str, model: type[Model]) -> QueryOptimizer:
        maybe_optimizer = self.select_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer

        self.select_related[name] = optimizer = QueryOptimizer(model=model, info=self.info, name=name, parent=self)
        return optimizer

    def add_prefetch_related(self, name: str, model: type[Model]) -> QueryOptimizer:
        maybe_optimizer = self.prefetch_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer

        self.prefetch_related[name] = optimizer = QueryOptimizer(model=model, info=self.info, name=name, parent=self)
        return optimizer
