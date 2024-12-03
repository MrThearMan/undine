from __future__ import annotations

import contextlib
import dataclasses
from typing import TYPE_CHECKING

from django.db import models
from django.db.models.constants import LOOKUP_SEP
from graphql import get_argument_values

from undine.converters import extend_expression
from undine.errors.exceptions import OptimizerError
from undine.optimizer.ast import GraphQLASTWalker, get_underlying_type
from undine.optimizer.prefetch_hack import evaluate_in_context
from undine.settings import undine_settings
from undine.utils.reflection import swappable_by_subclassing

if TYPE_CHECKING:
    from graphql import FieldNode, GraphQLOutputType

    from undine import QueryType
    from undine.typing import ExpressionLike, FilterCallback, GQLInfo, QuerySetCallback, ToManyField, ToOneField

__all__ = [
    "OptimizationData",
    "OptimizationResults",
    "QueryOptimizer",
]


@swappable_by_subclassing
class QueryOptimizer(GraphQLASTWalker):
    def __init__(self, model: type[models.Model], info: GQLInfo, *, max_complexity: int | None) -> None:
        """
        Optimize querysets based on the the given GraphQL resolve info.

        :param model: The model to start the optimization process from.
        :param info: The GraphQL resolve info for the request. These are the "instructions" the optimizer follows
                     to compile the needed optimizations.
        :param max_complexity: Maximum number of relations allowed in a the query.
                               Used to protect from malicious queries.
        """
        self.max_complexity = max_complexity
        self.optimization_data = OptimizationData(model=model)
        super().__init__(info=info, model=model)

    def optimize(self, queryset: models.QuerySet) -> models.QuerySet:
        """Optimize the given queryset."""
        self.run()  # Compile optimizations.
        results = self.process_optimizations(self.optimization_data)
        optimized_queryset = results.apply(queryset, self.info)
        evaluate_in_context(optimized_queryset, self.info)
        return optimized_queryset

    def process_optimizations(self, data: OptimizationData) -> OptimizationResults:
        """Process the given optimization data to OptimizerResults that can be applied to a queryset."""
        results = OptimizationResults(
            field_name=data.field_name,
            only_fields=data.only_fields,
            related_fields=data.related_fields,
            aliases=data.aliases,
            annotations=data.annotations,
            filter_callback=data.filter_callback,
            filters=data.filters,
            order_by=data.order_by,
            distinct=data.distinct,
        )

        for select_related_data in data.select_related.values():
            # Promote `select_related` to `prefetch_related` if any annotations are needed.
            if select_related_data.annotations:
                prefetch = self.process_prefetch(select_related_data)
                results.prefetch_related.append(prefetch)
                continue

            # Otherwise extend lookups to this model.
            nested_results = self.process_optimizations(select_related_data)
            results.extend(nested_results)

        for to_attr, prefetch_related_data in data.prefetch_related.items():
            # For GenericForeignKeys, we don't know the model, so we can't optimize the queryset.
            if prefetch_related_data.model is None:
                results.prefetch_related.append(prefetch_related_data.field_name)
                continue

            # Only need `to_attr` if it's different from the field name.
            if to_attr == prefetch_related_data.field_name:
                to_attr = None  # noqa: PLW2901

            prefetch = self.process_prefetch(prefetch_related_data, to_attr=to_attr)
            results.prefetch_related.append(prefetch)

        return results

    def process_prefetch(self, data: OptimizationData, *, to_attr: str | None = None) -> models.Prefetch:
        """Process prefetch related optimization data to a Prefetch object."""
        results = self.process_optimizations(data)

        if data.queryset_callback is not None:
            queryset = data.queryset_callback(self.info)
        else:
            queryset = data.model._meta.default_manager.get_queryset()

        optimized_queryset = results.apply(queryset, self.info)

        # TODO: Pagination.

        return models.Prefetch(data.field_name, optimized_queryset, to_attr=to_attr)

    def run_field_optimizer(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        """Run undine.Field optimization function for the given field."""
        undine_field = self.get_undine_field(field_type, field_node)
        if undine_field is not None and undine_field.optimizer_func is not None:
            undine_field.optimizer_func(undine_field, self.optimization_data)

    def parse_filter_info(self, parent_type: GraphQLOutputType, field_node: FieldNode) -> None:
        """Parse filtering and ordering information from the given field."""
        graphql_field = parent_type.fields[field_node.name.value]
        object_type = get_underlying_type(graphql_field.type)
        query_type = self.get_undine_query_type(object_type)
        if query_type is None:  # Not a undine field.
            return

        self.optimization_data.queryset_callback = query_type.__get_queryset__
        self.optimization_data.filter_callback = query_type.__filter_queryset__

        arg_values = get_argument_values(graphql_field, field_node, self.info.variable_values)

        if query_type.__filterset__:
            filter_data = arg_values.get(undine_settings.FILTER_INPUT_TYPE_KEY, {})
            filter_results = query_type.__filterset__.__build__(filter_data, self.info)

            self.optimization_data.filters.extend(filter_results.filters)
            self.optimization_data.distinct = self.optimization_data.distinct or filter_results.distinct
            self.optimization_data.aliases.update(filter_results.aliases)

        if query_type.__orderset__:
            order_data = arg_values.get(undine_settings.ORDER_BY_INPUT_TYPE_KEY, [])
            order_results = query_type.__orderset__.__build__(order_data, self.info)

            self.optimization_data.order_by.extend(order_results.order_by)

        query_type.__optimizer_hook__(self.optimization_data, self.info)

    def increase_complexity(self) -> None:
        super().increase_complexity()
        if self.max_complexity is not None and self.complexity > self.max_complexity:
            msg = f"Query complexity exceeds the maximum allowed of {self.max_complexity}"
            raise OptimizerError(msg)

    def handle_query_class(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        self.parse_filter_info(field_type, field_node)
        return super().handle_query_class(field_type, field_node)

    def handle_normal_field(self, field_type: GraphQLOutputType, field_node: FieldNode, field: models.Field) -> None:
        self.optimization_data.only_fields.append(field.get_attname())
        self.run_field_optimizer(field_type, field_node)

    def handle_to_one_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToOneField,
    ) -> None:
        from django.contrib.contenttypes.fields import GenericForeignKey  # noqa: PLC0415

        name = self.get_related_field_name(related_field)

        if isinstance(related_field, GenericForeignKey):
            data = self.optimization_data.add_prefetch_related(name)
        else:
            data = self.optimization_data.add_select_related(name)

        if isinstance(related_field, models.ForeignKey):
            self.optimization_data.related_fields.append(related_field.attname)

        if isinstance(related_field, GenericForeignKey):
            self.optimization_data.related_fields.append(related_field.ct_field)
            self.optimization_data.related_fields.append(related_field.fk_field)

        self.run_field_optimizer(parent_type, field_node)

        with self.use_data(data):
            self.parse_filter_info(parent_type, field_node)
            super().handle_to_one_field(parent_type, field_node, related_field)

    def handle_to_many_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToManyField,
    ) -> None:
        from django.contrib.contenttypes.fields import GenericRelation  # noqa: PLC0415

        name = self.get_related_field_name(related_field)

        alias: str | None = getattr(field_node.alias, "value", None)
        to_attr = alias if alias is not None else name

        data = self.optimization_data.add_prefetch_related(name, to_attr=to_attr)

        if isinstance(related_field, models.ManyToOneRel):
            data.related_fields.append(related_field.field.attname)

        if isinstance(related_field, GenericRelation):
            data.related_fields.append(related_field.object_id_field_name)
            data.related_fields.append(related_field.content_type_field_name)

        self.run_field_optimizer(parent_type, field_node)

        with self.use_data(data):
            self.parse_filter_info(parent_type, field_node)
            super().handle_to_many_field(parent_type, field_node, related_field)

    def handle_custom_field(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        self.run_field_optimizer(field_type, field_node)

    @contextlib.contextmanager
    def use_data(self, nested_data: OptimizationData) -> None:
        original = self.optimization_data
        try:
            self.optimization_data = nested_data
            yield
        finally:
            self.optimization_data = original


@dataclasses.dataclass(slots=True)
class OptimizationData:
    """
    Holds QueryOptimizer optimization data. Will be processed by the QueryOptimizer to OptimizerResults
    when the optimization compilation is complete, which can then be used to optimize a queryset.
    """

    model: type[models.Model] | None  # Will be 'None' for GenericForeignKeys.
    field_name: str | None = None  # Will be 'None' if there is no parent.
    parent: OptimizationData | None = None

    only_fields: list[str] = dataclasses.field(default_factory=list)
    related_fields: list[str] = dataclasses.field(default_factory=list)
    aliases: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    annotations: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    select_related: dict[str, OptimizationData] = dataclasses.field(default_factory=dict)
    prefetch_related: dict[str, OptimizationData] = dataclasses.field(default_factory=dict)

    filters: list[models.Q] = dataclasses.field(default_factory=list)
    order_by: list[models.OrderBy] = dataclasses.field(default_factory=list)
    distinct: bool = False

    queryset_callback: QuerySetCallback | None = None
    filter_callback: FilterCallback | None = None

    def add_select_related(
        self,
        field_name: str,
        *,
        query_type: type[QueryType] | None = None,
    ) -> OptimizationData:
        """Add a 'select_related' optimization for the given field."""
        maybe_optimizer = self.select_related.get(field_name)
        if maybe_optimizer is not None:
            return maybe_optimizer

        if query_type is not None:
            model: type[models.Model] = query_type.__model__
        else:
            model = self.model._meta.get_field(field_name).related_model  # type: ignore[attr-defined]

        data = OptimizationData(model=model, field_name=field_name, parent=self)

        if query_type is not None:
            data.queryset_callback = query_type.__get_queryset__
            data.filter_callback = query_type.__filter_queryset__

        self.select_related[field_name] = data
        return data

    def add_prefetch_related(
        self,
        field_name: str,
        *,
        query_type: type[QueryType] | None = None,
        to_attr: str | None = None,
    ) -> OptimizationData:
        """Add a 'prefetch_related' optimization for the given field."""
        maybe_optimizer = self.prefetch_related.get(to_attr or field_name)
        if maybe_optimizer is not None:
            return maybe_optimizer

        if query_type is not None:
            model: type[models.Model] | None = query_type.__model__
        else:
            model = self.model._meta.get_field(field_name).related_model  # type: ignore[attr-defined]

        data = OptimizationData(model=model, field_name=field_name, parent=self)

        if query_type is not None:
            data.queryset_callback = query_type.__get_queryset__
            data.filter_callback = query_type.__filter_queryset__

        self.prefetch_related[to_attr or field_name] = data
        return data


@dataclasses.dataclass(slots=True)
class OptimizationResults:
    """Optimizations that can be applied to a queryset."""

    field_name: str | None = None

    # Field optimizations
    only_fields: list[str] = dataclasses.field(default_factory=list)
    related_fields: list[str] = dataclasses.field(default_factory=list)
    aliases: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    annotations: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[models.Prefetch | str] = dataclasses.field(default_factory=list)

    # Filters
    filter_callback: FilterCallback | None = None
    filters: list[models.Q] = dataclasses.field(default_factory=list)
    order_by: list[models.OrderBy] = dataclasses.field(default_factory=list)
    distinct: bool = False

    def apply(self, queryset: models.QuerySet, info: GQLInfo) -> models.QuerySet:
        """Apply the optimization results to the given queryset."""
        if self.select_related:
            queryset = queryset.select_related(*self.select_related)
        if self.prefetch_related:
            queryset = queryset.prefetch_related(*self.prefetch_related)
        if not undine_settings.DISABLE_ONLY_FIELDS_OPTIMIZATION and (self.only_fields or self.related_fields):
            queryset = queryset.only(*self.only_fields, *self.related_fields)
        if self.aliases:
            queryset = queryset.alias(**self.aliases)
        if self.annotations:
            queryset = queryset.annotate(**self.annotations)

        if self.filter_callback is not None:
            queryset = self.filter_callback(queryset, info)

        if self.order_by:
            queryset = queryset.order_by(*self.order_by)
        for ftr in self.filters:
            queryset = queryset.filter(ftr)
        if self.distinct:
            queryset = queryset.distinct()
        return queryset

    def extend(self, other: OptimizationResults) -> OptimizationResults:
        """
        Extend the given optimization results to this one
        by prefexing their lookups using the other's `field_name`.
        """
        self.select_related.append(other.field_name)
        self.only_fields.extend(f"{other.field_name}{LOOKUP_SEP}{only}" for only in other.only_fields)
        self.related_fields.extend(f"{other.field_name}{LOOKUP_SEP}{only}" for only in other.related_fields)
        self.select_related.extend(f"{other.field_name}{LOOKUP_SEP}{select}" for select in other.select_related)

        for prefetch in other.prefetch_related:
            if isinstance(prefetch, str):
                self.prefetch_related.append(f"{other.field_name}{LOOKUP_SEP}{prefetch}")
            if isinstance(prefetch, models.Prefetch):
                prefetch.add_prefix(other.field_name)
                self.prefetch_related.append(prefetch)

        self.filters.extend(extend_expression(ftr, field_name=other.field_name) for ftr in other.filters)
        self.order_by.extend(extend_expression(order, field_name=other.field_name) for order in other.order_by)
        self.distinct = other.distinct or self.distinct

        return self
