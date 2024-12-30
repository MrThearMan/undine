from __future__ import annotations

import contextlib
import dataclasses
from functools import partial
from typing import TYPE_CHECKING, Self

from django.db.models import Field, ForeignKey, ManyToOneRel, Model, OrderBy, Prefetch, Q, QuerySet
from django.db.models.constants import LOOKUP_SEP
from graphql import GraphQLScalarType, get_argument_values

from undine.converters import extend_expression
from undine.errors.exceptions import OptimizerError
from undine.settings import undine_settings
from undine.utils.reflection import is_same_func, swappable_by_subclassing

from .ast import GraphQLASTWalker, get_underlying_type, is_connection

if TYPE_CHECKING:
    from graphql import FieldNode, GraphQLOutputType

    from undine import QueryType
    from undine.relay import PaginationHandler
    from undine.typing import (
        CalculationResolver,
        ExpressionLike,
        FilterCallback,
        GQLInfo,
        ModelField,
        QuerySetCallback,
        RelatedField,
        ToManyField,
        ToOneField,
    )

__all__ = [
    "OptimizationData",
    "OptimizationResults",
    "QueryOptimizer",
]


@swappable_by_subclassing
class QueryOptimizer(GraphQLASTWalker):
    def __init__(self, *, model: type[Model], info: GQLInfo, max_complexity: int | None) -> None:
        """
        Optimize querysets based on the given GraphQL resolve info.

        :param model: The Django `Model` to start the optimization process from.
        :param info: The GraphQL resolve info for the request. These are the "instructions" the optimizer follows
                     to compile the needed optimizations.
        """
        self.max_complexity = max_complexity
        self.optimization_data = OptimizationData(model=model)
        super().__init__(info=info, model=model)

    def optimize(self, queryset: QuerySet) -> QuerySet:
        """Optimize the given queryset."""
        self.run()  # Compile optimizations.
        results = self.process_optimizations(self.optimization_data)
        return results.apply(queryset, self.root_info)

    def process_optimizations(self, data: OptimizationData) -> OptimizationResults:
        """Process the given optimization data to OptimizerResults that can be applied to a queryset."""
        model_field: ModelField | None = None
        if data.parent is not None and data.field_name is not None:
            model_field = data.parent.model._meta.get_field(data.field_name)

        results = OptimizationResults(
            related_field=model_field,
            only_fields=data.only_fields,
            aliases=data.aliases,
            annotations=data.annotations,
            filters=data.filters,
            order_by=data.order_by,
            distinct=data.distinct,
            none=data.none,
            pagination=data.pagination,
            pre_filter_callback=data.pre_filter_callback,
            post_filter_callback=data.post_filter_callback,
            field_calculations=data.field_calculations,
        )

        for select_related_data in data.select_related.values():
            # Check if we need to prefetch instead of joining.
            if select_related_data.should_promote_to_prefetch():
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

    def process_prefetch(self, data: OptimizationData, *, to_attr: str | None = None) -> Prefetch:
        """Process prefetch related optimization data to a Prefetch object."""
        results = self.process_optimizations(data)
        queryset = data.queryset_callback(self.root_info)
        optimized_queryset = results.apply(queryset, self.root_info)
        return Prefetch(data.field_name, optimized_queryset, to_attr=to_attr)

    def run_undine_field_hooks(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        """Run `undine.Field` hooks if the field has the undine field in its extension."""
        undine_field = self.get_undine_field(field_type, field_node)
        if undine_field is None:
            return

        if undine_field.optimizer_func is not None:
            undine_field.optimizer_func(undine_field, self.optimization_data)

        if undine_field.calculate_func is not None:
            graphql_field = field_type.fields[field_node.name.value]
            arg_values = get_argument_values(graphql_field, field_node, self.root_info.variable_values)
            func = partial(undine_field.calculate_func, undine_field, **arg_values)
            self.optimization_data.field_calculations.append(func)

    def parse_filter_info(self, parent_type: GraphQLOutputType, field_node: FieldNode) -> None:
        """Parse filtering and ordering information from the given field."""
        graphql_field = parent_type.fields[field_node.name.value]
        object_type = get_underlying_type(graphql_field.type)

        arg_values = get_argument_values(graphql_field, field_node, self.root_info.variable_values)

        if is_connection(object_type):
            undine_connection = self.get_undine_connection(object_type)
            if undine_connection is None:  # pragma: no cover
                return

            edge_type = get_underlying_type(object_type.fields["edges"].type)
            object_type = get_underlying_type(edge_type.fields["node"].type)

            self.optimization_data.pagination = undine_connection.pagination_handler(
                typename=object_type.name,
                first=arg_values.get("first"),
                last=arg_values.get("last"),
                offset=arg_values.get("offset"),
                after=arg_values.get("after"),
                before=arg_values.get("before"),
                max_limit=undine_connection.max_limit,
            )

        query_type = self.get_undine_query_type(object_type)
        if query_type is None:  # Not an undine field.
            return

        self.optimization_data.fill_from_query_type(query_type=query_type)

        if query_type.__filterset__:
            filter_data = arg_values.get(undine_settings.FILTER_INPUT_TYPE_KEY, {})
            filter_results = query_type.__filterset__.__build__(filter_data, self.root_info)

            self.optimization_data.filters.extend(filter_results.filters)
            self.optimization_data.aliases |= filter_results.aliases
            self.optimization_data.distinct |= filter_results.distinct
            self.optimization_data.none |= filter_results.none

        if query_type.__orderset__:
            order_data = arg_values.get(undine_settings.ORDER_BY_INPUT_TYPE_KEY, [])
            order_results = query_type.__orderset__.__build__(order_data, self.root_info)

            self.optimization_data.order_by.extend(order_results.order_by)

        query_type.__optimizer_hook__(self.optimization_data, self.root_info)

    def increase_complexity(self) -> None:
        super().increase_complexity()
        if self.max_complexity is not None and self.complexity > self.max_complexity:
            msg = f"Query complexity exceeds the maximum allowed of {self.max_complexity}"
            raise OptimizerError(msg)

    def handle_query_class(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        self.parse_filter_info(field_type, field_node)
        return super().handle_query_class(field_type, field_node)

    def handle_total_count(self, scalar: GraphQLScalarType, field_node: FieldNode) -> None:
        if self.optimization_data.pagination is not None:
            self.optimization_data.pagination.requires_total_count = True

    def handle_page_info_field(self, parent_type: GraphQLOutputType, field_node: FieldNode) -> None:
        if self.optimization_data.pagination is not None and field_node.name.value != "hasNextPage":
            self.optimization_data.pagination.requires_total_count = True

    def handle_normal_field(self, field_type: GraphQLOutputType, field_node: FieldNode, field: Field) -> None:
        self.optimization_data.only_fields.append(field.get_attname())
        self.run_undine_field_hooks(field_type, field_node)

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

        if isinstance(related_field, ForeignKey):
            self.optimization_data.only_fields.append(related_field.attname)

        if isinstance(related_field, GenericForeignKey):
            self.optimization_data.only_fields.append(related_field.ct_field)
            self.optimization_data.only_fields.append(related_field.fk_field)

        self.run_undine_field_hooks(parent_type, field_node)

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
        data = self.optimization_data.add_prefetch_related(name, to_attr=alias)

        if isinstance(related_field, ManyToOneRel):
            data.only_fields.append(related_field.field.attname)

        if isinstance(related_field, GenericRelation):
            data.only_fields.append(related_field.object_id_field_name)
            data.only_fields.append(related_field.content_type_field_name)

        self.run_undine_field_hooks(parent_type, field_node)

        with self.use_data(data):
            self.parse_filter_info(parent_type, field_node)
            super().handle_to_many_field(parent_type, field_node, related_field)

    def handle_custom_field(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        self.run_undine_field_hooks(field_type, field_node)

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

    model: type[Model] | None  # Will be 'None' for GenericForeignKeys.
    field_name: str | None = None  # Will be 'None' if there is no parent.
    parent: OptimizationData | None = None

    only_fields: list[str] = dataclasses.field(default_factory=list)
    aliases: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    annotations: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    select_related: dict[str, OptimizationData] = dataclasses.field(default_factory=dict)
    prefetch_related: dict[str, OptimizationData] = dataclasses.field(default_factory=dict)

    filters: list[Q] = dataclasses.field(default_factory=list)
    order_by: list[OrderBy] = dataclasses.field(default_factory=list)
    distinct: bool = False
    none: bool = False
    pagination: PaginationHandler | None = None

    queryset_callback: QuerySetCallback = dataclasses.field(init=False)
    pre_filter_callback: FilterCallback | None = None
    post_filter_callback: FilterCallback | None = None
    field_calculations: list[CalculationResolver] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        def default_queryset_callback(info: GQLInfo) -> QuerySet:
            return self.model._meta.default_manager.get_queryset()

        self.queryset_callback = default_queryset_callback

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

        model: type[Model] = self.model._meta.get_field(field_name).related_model  # type: ignore[attr-defined]

        data = OptimizationData(model=model, field_name=field_name, parent=self)
        if query_type is not None:
            data.fill_from_query_type(query_type=query_type)

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
        name = to_attr or field_name
        maybe_optimizer = self.prefetch_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer

        model: type[Model] = self.model._meta.get_field(field_name).related_model  # type: ignore[attr-defined]

        data = OptimizationData(model=model, field_name=field_name, parent=self)
        if query_type is not None:
            data.fill_from_query_type(query_type=query_type)

        self.prefetch_related[name] = data
        return data

    def should_promote_to_prefetch(self) -> bool:
        """
        If this is a `to-one` related field on some other field, should its results be fetched with
        `prefetch_related` instead of `select_related`?

        E.g. If the model instances need to be annotated, we need to prefetch to retain those annotations.
        Or if we have filtering that always needs to be done on the related objects.
        """
        return (
            bool(self.annotations)
            or bool(self.aliases)
            or bool(self.field_calculations)
            or self.pre_filter_callback is not None
            or self.post_filter_callback is not None
        )

    def fill_from_query_type(self, query_type: type[QueryType]) -> Self:
        """Fill the optimization data from the given QueryType."""
        from undine import FilterSet, QueryType  # noqa: PLC0415

        self.model = query_type.__model__
        self.queryset_callback = query_type.__get_queryset__

        # Only include pre-filter callback if it's different from the default.
        if not is_same_func(query_type.__filter_queryset__, QueryType.__filter_queryset__):
            self.pre_filter_callback = query_type.__filter_queryset__

        # Only include post-filter callback if it's different from the default.
        if (
            query_type.__filterset__  # Has filterset
            and not is_same_func(query_type.__filterset__.__filter_queryset__, FilterSet.__filter_queryset__)
        ):
            self.post_filter_callback = query_type.__filterset__.__filter_queryset__

        return self


@dataclasses.dataclass(slots=True)
class OptimizationResults:
    """Optimizations that can be applied to a queryset."""

    # The model field for a relation, if these are the results for a prefetch.
    related_field: RelatedField | None = None

    # Field optimizations
    only_fields: list[str] = dataclasses.field(default_factory=list)
    aliases: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    annotations: dict[str, ExpressionLike] = dataclasses.field(default_factory=dict)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[Prefetch | str] = dataclasses.field(default_factory=list)

    # Filtering
    filters: list[Q] = dataclasses.field(default_factory=list)
    order_by: list[OrderBy] = dataclasses.field(default_factory=list)
    distinct: bool = False
    none: bool = False
    pagination: PaginationHandler | None = None

    pre_filter_callback: FilterCallback | None = None
    post_filter_callback: FilterCallback | None = None
    field_calculations: list[CalculationResolver] = dataclasses.field(default_factory=list)

    def apply(self, queryset: QuerySet, info: GQLInfo) -> QuerySet:  # noqa: C901, PLR0912
        """Apply the optimization results to the given queryset."""
        if self.none:
            return queryset.none()

        if self.select_related:
            queryset = queryset.select_related(*self.select_related)
        if self.prefetch_related:
            queryset = queryset.prefetch_related(*self.prefetch_related)
        if not undine_settings.DISABLE_ONLY_FIELDS_OPTIMIZATION and self.only_fields:
            queryset = queryset.only(*self.only_fields)
        if self.aliases:
            queryset = queryset.alias(**self.aliases)
        if self.annotations:
            queryset = queryset.annotate(**self.annotations)

        if self.pre_filter_callback is not None:
            queryset = self.pre_filter_callback(queryset, info)

        if self.order_by:
            queryset = queryset.order_by(*self.order_by)
        if self.distinct:
            queryset = queryset.distinct()

        for field_calculation in self.field_calculations:
            queryset = field_calculation(queryset, info)

        for ftr in self.filters:
            queryset = queryset.filter(ftr)

        if self.post_filter_callback is not None:
            queryset = self.post_filter_callback(queryset, info)

        if self.pagination is not None:
            if self.related_field is None:
                queryset = self.pagination.paginate_queryset(queryset)
            else:
                queryset = self.pagination.paginate_prefetch_queryset(queryset, self.related_field)

        return queryset

    def extend(self, other: Self) -> Self:
        """
        Extend the given optimization results to this one
        by prefexing their lookups using the other's `field_name`.
        """
        self.select_related.append(other.related_field.name)
        self.only_fields.extend(f"{other.related_field.name}{LOOKUP_SEP}{only}" for only in other.only_fields)
        self.select_related.extend(f"{other.related_field.name}{LOOKUP_SEP}{select}" for select in other.select_related)

        for prefetch in other.prefetch_related:
            if isinstance(prefetch, str):
                self.prefetch_related.append(f"{other.related_field.name}{LOOKUP_SEP}{prefetch}")
            if isinstance(prefetch, Prefetch):
                prefetch.add_prefix(other.related_field.name)
                self.prefetch_related.append(prefetch)

        self.filters.extend(extend_expression(ftr, field_name=other.related_field.name) for ftr in other.filters)
        self.order_by.extend(extend_expression(order, field_name=other.related_field.name) for order in other.order_by)
        self.distinct |= other.distinct
        self.none |= other.none

        return self
