from __future__ import annotations

import contextlib
import dataclasses
from typing import TYPE_CHECKING

from django.db.models import ForeignKey, ManyToOneRel, Prefetch
from django.db.models.constants import LOOKUP_SEP
from graphql import get_argument_values
from graphql.execution.execute import get_field_def

from undine.converters import extend_expression_to_joined_table
from undine.errors.exceptions import OptimizerError
from undine.optimizer.ast import GraphQLASTWalker, get_underlying_type
from undine.optimizer.prefetch_hack import evaluate_in_context
from undine.settings import undine_settings
from undine.utils.reflection import swappable_by_subclassing

if TYPE_CHECKING:
    from django.db import models
    from graphql import FieldNode, GraphQLOutputType

    from undine import Field, QueryType
    from undine.typing import ExpressionLike, GQLInfo, ToManyField, ToOneField

__all__ = [
    "QueryOptimizer",
]


@swappable_by_subclassing
class QueryOptimizer(GraphQLASTWalker):
    """A class for compiling query optimizations and applying them to a queryset."""

    def __init__(self, query_type: type[QueryType], info: GQLInfo, max_complexity: int | None = None) -> None:
        """
        Initialize the optimization compiler with the query info.

        :param max_complexity: How many 'select_related' and 'prefetch_related' table joins are allowed.
                               Used to protect from malicious queries.
        """
        self.max_complexity = max_complexity or undine_settings.OPTIMIZER_MAX_COMPLEXITY
        self.processor = OptimizationProcessor(query_type, info)
        self.to_attr: str | None = None
        super().__init__(info=info, model=query_type.__model__)

    def optimize(self, queryset: models.QuerySet) -> models.QuerySet:
        """
        Compile optimizations for the given queryset.

        :return: QueryOptimizer instance that can perform any needed optimization,
                 or None if queryset is already optimized.
        """
        self.run()
        results = self.processor.process()
        optimized_queryset = results.apply(queryset, self.info)
        evaluate_in_context(optimized_queryset, self.info)
        return optimized_queryset

    def increase_complexity(self) -> None:
        super().increase_complexity()
        if self.complexity > self.max_complexity:
            msg = f"Query complexity exceeds the maximum allowed of {self.max_complexity}"
            raise OptimizerError(msg)

    def parse_filter_info(self, parent_type: GraphQLOutputType, field_node: FieldNode) -> None:
        graphql_field = get_field_def(self.info.schema, parent_type, field_node)
        object_type = get_underlying_type(graphql_field.type)
        model_type = self.get_model_type(object_type)
        if model_type is None:
            return

        self.processor.model_type = model_type
        arg_values = get_argument_values(graphql_field, field_node, self.info.variable_values)

        if model_type.__filterset__:
            filter_data = arg_values.get(undine_settings.FILTER_INPUT_TYPE_KEY, {})
            filter_results = model_type.__filterset__.__build__(filter_data, self.info)

            self.processor.filters.extend(filter_results.filters)
            self.processor.distinct = self.processor.distinct or filter_results.distinct
            self.processor.aliases.update(filter_results.aliases)

        if model_type.__orderset__:
            order_data = arg_values.get(undine_settings.ORDER_BY_INPUT_TYPE_KEY, [])
            order_results = model_type.__orderset__.__build__(order_data, self.info)

            self.processor.order_by.extend(order_results.order_by)

        model_type.__optimizer_hook__(self.processor)

    def handle_query_class(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        self.parse_filter_info(field_type, field_node)
        return super().handle_query_class(field_type, field_node)

    def handle_normal_field(self, field_type: GraphQLOutputType, field_node: FieldNode, field: models.Field) -> None:
        self.processor.only_fields.append(field.get_attname())
        self.run_field_optimizer(field_type, field_node)

    def handle_to_one_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[models.Model] | None,
    ) -> None:
        from django.contrib.contenttypes.fields import GenericForeignKey  # noqa: PLC0415

        graphql_field = get_field_def(self.info.schema, parent_type, field_node)
        object_type = get_underlying_type(graphql_field.type)
        query_type = self.get_model_type(object_type)

        name = self.get_related_field_name(related_field)
        processor = OptimizationProcessor(query_type, self.info, name, self.processor)

        if isinstance(related_field, GenericForeignKey):
            processor = self.processor.prefetch_related.setdefault(name, processor)
        else:
            processor = self.processor.select_related.setdefault(name, processor)

        if isinstance(related_field, ForeignKey):
            self.processor.related_fields.append(related_field.attname)

        if isinstance(related_field, GenericForeignKey):
            self.processor.related_fields.append(related_field.ct_field)
            self.processor.related_fields.append(related_field.fk_field)

        self.run_field_optimizer(parent_type, field_node)

        with self.use_processor(processor):
            self.parse_filter_info(parent_type, field_node)
            super().handle_to_one_field(parent_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[models.Model] | None,
    ) -> None:
        from django.contrib.contenttypes.fields import GenericRelation  # noqa: PLC0415

        name = self.get_related_field_name(related_field)
        alias = getattr(field_node.alias, "value", None)
        key = self.to_attr if self.to_attr is not None else alias if alias is not None else name
        self.to_attr = None

        graphql_field = get_field_def(self.info.schema, parent_type, field_node)
        object_type = get_underlying_type(graphql_field.type)
        query_type = self.get_model_type(object_type)

        processor = OptimizationProcessor(query_type, self.info, name, self.processor)
        processor = self.processor.prefetch_related.setdefault(key, processor)

        if isinstance(related_field, ManyToOneRel):
            processor.related_fields.append(related_field.field.attname)

        if isinstance(related_field, GenericRelation):
            processor.related_fields.append(related_field.object_id_field_name)
            processor.related_fields.append(related_field.content_type_field_name)

        self.run_field_optimizer(parent_type, field_node)

        with self.use_processor(processor):
            self.parse_filter_info(parent_type, field_node)
            super().handle_to_many_field(parent_type, field_node, related_field, related_model)

    def handle_custom_field(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        self.run_field_optimizer(field_type, field_node)

    def run_field_optimizer(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        undine_field = self.get_undine_field(field_type, field_node)
        if undine_field is not None and undine_field.optimizer_func is not None:
            undine_field.optimizer_func(undine_field, self.processor)

    def get_undine_field(self, field_type: GraphQLOutputType, field_node: FieldNode) -> Field | None:
        field = field_type.fields.get(field_node.name.value)
        if field is None:
            return None
        return field.extensions.get(undine_settings.FIELD_EXTENSIONS_KEY)

    @contextlib.contextmanager
    def use_processor(self, processor: OptimizationProcessor) -> None:
        original = self.processor
        try:
            self.processor = processor
            yield
        finally:
            self.processor = original


@swappable_by_subclassing
class OptimizationProcessor:
    """Processor for storing optimization data and processing them to results that can be applied to a queryset."""

    def __init__(
        self,
        query_type: type[QueryType],
        info: GQLInfo,
        name: str | None = None,
        parent: OptimizationProcessor | None = None,
    ) -> None:
        self.info = info
        self.name = name
        self.parent = parent
        self.model_type: type[QueryType] = query_type

        self.filters: list[models.Q] = []
        self.order_by: list[models.OrderBy] = []
        self.distinct: bool = False

        self.only_fields: list[str] = []
        self.related_fields: list[str] = []
        self.aliases: dict[str, ExpressionLike] = {}
        self.annotations: dict[str, ExpressionLike] = {}
        self.select_related: dict[str, OptimizationProcessor] = {}
        self.prefetch_related: dict[str, OptimizationProcessor] = {}

    def process(self) -> OptimizationResults:
        """Process compiled optimizations with the given filter info."""
        results = OptimizationResults(
            name=self.name,
            model_type=self.model_type,
            only_fields=self.only_fields,
            related_fields=self.related_fields,
            aliases=self.aliases,
            annotations=self.annotations,
            filters=self.filters,
            order_by=self.order_by,
            distinct=self.distinct,
        )

        for name, processor in self.select_related.items():
            nested_results = processor.process()

            # Promote `select_related` to `prefetch_related` if any annotations are needed.
            if processor.annotations:
                prefetch = processor.process_prefetch(name, nested_results)
                results.prefetch_related.append(prefetch)
                continue

            # Otherwise extend lookups to this model.
            results += nested_results

        for name, processor in self.prefetch_related.items():
            # For generic foreign keys, we don't know the model, so we can't optimize the queryset.
            if processor.model_type is None:
                results.prefetch_related.append(processor.name)
                continue

            nested_results = processor.process()

            prefetch = processor.process_prefetch(name, nested_results)
            results.prefetch_related.append(prefetch)

        return results

    def process_prefetch(self, to_attr: str, results: OptimizationResults) -> Prefetch:
        """Process a prefetch, optimizing its queryset based on the given filter info."""
        queryset = self.model_type.__get_queryset__(self.info)
        optimized_queryset = results.apply(queryset, self.info)
        # TODO: Pagination.
        return Prefetch(self.name, optimized_queryset, to_attr=to_attr if to_attr != self.name else None)

    def add_select_related(self, name: str) -> OptimizationProcessor:
        maybe_optimizer = self.select_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer

        query_type = self.model_type.__field_map__[name].ref
        self.select_related[name] = processor = OptimizationProcessor(query_type, self.info, name, self)
        return processor

    def add_prefetch_related(self, name: str) -> OptimizationProcessor:
        maybe_optimizer = self.prefetch_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer

        query_type = self.model_type.__field_map__[name].ref
        self.prefetch_related[name] = processor = OptimizationProcessor(query_type, self.info, name, self)
        return processor


@dataclasses.dataclass
class OptimizationResults:
    """Results of optimizations to be applied to a queryset."""

    name: str | None = None
    model_type: type[QueryType] | None = None

    # Optimizations
    only_fields: list[str] = dataclasses.field(default_factory=list)
    related_fields: list[str] = dataclasses.field(default_factory=list)
    aliases: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    annotations: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[Prefetch | str] = dataclasses.field(default_factory=list)

    # Filters
    filters: list[models.Q] = dataclasses.field(default_factory=list)
    order_by: list[models.OrderBy] = dataclasses.field(default_factory=list)
    distinct: bool = False

    def apply(self, queryset: models.QuerySet, info: GQLInfo) -> models.QuerySet:
        """Apply optimization results to the given queryset."""
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

        if self.model_type is not None:
            queryset = self.model_type.__filter_queryset__(queryset, info)

        if self.order_by:
            queryset = queryset.order_by(*self.order_by)
        for ftr in self.filters:
            queryset = queryset.filter(ftr)
        if self.distinct:
            queryset = queryset.distinct()
        return queryset

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

        # TODO: Should these be exteded?
        self.order_by.extend(extend_expression_to_joined_table(order, other.name) for order in other.order_by)
        self.filters.extend(extend_expression_to_joined_table(ftr, other.name) for ftr in other.filters)
        self.distinct = other.distinct or self.distinct

        return self
