from __future__ import annotations

import dataclasses
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db.models import ForeignKey, ManyToOneRel, OneToOneRel, Prefetch
from django.db.models.constants import LOOKUP_SEP
from graphql import InlineFragmentNode, get_argument_values

from undine.converters import extend_expression
from undine.exceptions import GraphQLTooManyFiltersError, GraphQLTooManyOrdersError
from undine.settings import undine_settings
from undine.utils.graphql.undine_extensions import get_undine_connection, get_undine_field, get_undine_query_type
from undine.utils.graphql.utils import get_underlying_type, is_connection, is_typename_metafield, should_skip_node
from undine.utils.model_utils import get_default_manager, get_related_field_name
from undine.utils.reflection import is_same_func

from .ast_walker import GraphQLASTWalker

if TYPE_CHECKING:
    from collections.abc import Generator

    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models import Field, Model, OrderBy, Q, QuerySet
    from graphql import FieldNode, GraphQLInterfaceType, GraphQLObjectType, GraphQLScalarType

    from undine import Calculation, QueryType
    from undine.relay import PaginationHandler
    from undine.typing import (
        DjangoExpression,
        FilterCallback,
        GQLInfo,
        QuerySetCallback,
        RelatedField,
        Selections,
        TModel,
        ToManyField,
        ToOneField,
    )

__all__ = [
    "OptimizationData",
    "OptimizationResults",
    "QueryOptimizer",
]


class QueryOptimizer(GraphQLASTWalker):
    """A class for processing the given GraphQL resolve info into required optimizations."""

    def __init__(self, *, model: type[Model], info: GQLInfo) -> None:
        """
        Optimize querysets based on the given GraphQL resolve info.

        :param model: The Django `Model` to start the optimization process from. Can be `None`
                      if the optimization is for a union of types.
        :param info: The GraphQL resolve info for the request. These are the "instructions" the optimizer follows
                     to compile the needed optimizations.
        """
        self.optimization_data = OptimizationData(model=model, info=info)
        super().__init__(info=info, model=model)

    def compile(self) -> OptimizationResults:
        self.run()
        return self.optimization_data.process()

    def parse_filter_info(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        """Parse filtering and ordering information from the given field."""
        graphql_field = parent_type.fields[field_node.name.value]
        object_type: GraphQLObjectType = get_underlying_type(graphql_field.type)  # type: ignore[assignment]

        arg_values = get_argument_values(graphql_field, field_node, self.info.variable_values)

        if is_connection(object_type):
            undine_connection = get_undine_connection(object_type)
            if undine_connection is None:  # pragma: no cover
                return

            edge_type: GraphQLObjectType = get_underlying_type(object_type.fields["edges"].type)  # type: ignore[assignment]
            object_type = get_underlying_type(edge_type.fields["node"].type)  # type: ignore[assignment]

            self.optimization_data.pagination = undine_connection.pagination_handler(
                typename=object_type.name,
                first=arg_values.get("first"),
                last=arg_values.get("last"),
                offset=arg_values.get("offset"),
                after=arg_values.get("after"),
                before=arg_values.get("before"),
                page_size=undine_connection.page_size,
            )

        query_type = get_undine_query_type(object_type)
        if query_type is not None:
            self.handle_undine_query_type(query_type, arg_values)

    def handle_undine_query_type(self, query_type: type[QueryType], arg_values: dict[str, Any]) -> None:
        self.optimization_data.fill_from_query_type(query_type=query_type)

        if query_type.__filterset__:
            filter_data = arg_values.get(undine_settings.QUERY_TYPE_FILTER_INPUT_KEY, {})
            filter_results = query_type.__filterset__.__build__(filter_data, self.info)

            if filter_results.filter_count > undine_settings.MAX_FILTERS_PER_TYPE:
                raise GraphQLTooManyFiltersError(
                    name=query_type.__filterset__.__schema_name__,
                    filter_count=filter_results.filter_count,
                    max_count=undine_settings.MAX_FILTERS_PER_TYPE,
                )

            self.optimization_data.filters.extend(filter_results.filters)
            self.optimization_data.aliases |= filter_results.aliases
            self.optimization_data.distinct |= filter_results.distinct
            self.optimization_data.none |= filter_results.none

        if query_type.__orderset__:
            order_data = arg_values.get(undine_settings.QUERY_TYPE_ORDER_INPUT_KEY, [])
            order_results = query_type.__orderset__.__build__(order_data, self.info)

            if order_results.order_count > undine_settings.MAX_ORDERS_PER_TYPE:
                raise GraphQLTooManyOrdersError(
                    name=query_type.__orderset__.__schema_name__,
                    filter_count=order_results.order_count,
                    max_count=undine_settings.MAX_ORDERS_PER_TYPE,
                )

            self.optimization_data.order_by.extend(order_results.order_by)

        query_type.__optimizations__(self.optimization_data, self.info)

    def handle_undine_field(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        """Handle any special operations for undine Fields."""
        graphql_field = parent_type.fields[field_node.name.value]
        undine_field = get_undine_field(graphql_field)
        if undine_field is None:
            return

        if undine_field.optimizer_func is not None:
            undine_field.optimizer_func(undine_field, self.optimization_data, self.info)

    def handle_query_class(self, field_type: GraphQLObjectType, field_node: FieldNode) -> None:
        self.parse_filter_info(field_type, field_node)
        super().handle_query_class(field_type, field_node)

    def handle_total_count(self, scalar: GraphQLScalarType, field_node: FieldNode) -> None:
        if self.optimization_data.pagination is not None:
            self.optimization_data.pagination.requires_total_count = True

    def handle_page_info_field(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        # To know if there is a next page, we must get total count.
        if self.optimization_data.pagination is not None and field_node.name.value != "hasNextPage":
            self.optimization_data.pagination.requires_total_count = True

    def handle_normal_field(self, parent_type: GraphQLObjectType, field_node: FieldNode, field: Field) -> None:
        # Aliases not accounted for since there is no filtering
        field_name = field.get_attname()
        self.optimization_data.only_fields.add(field_name)
        self.handle_undine_field(parent_type, field_node)

    def handle_to_one_field(
        self,
        parent_type: GraphQLObjectType,
        field_node: FieldNode,
        related_field: ToOneField,
    ) -> None:
        name = get_related_field_name(related_field)

        # Aliases not accounted for since there is no filtering
        data = self.optimization_data.add_select_related(name)

        if isinstance(related_field, ForeignKey):
            self.optimization_data.only_fields.add(related_field.attname)

        elif isinstance(related_field, OneToOneRel):
            data.only_fields.add(related_field.field.attname)

        self.handle_undine_field(parent_type, field_node)

        data.info = self.info
        with self.use_data(data):
            self.parse_filter_info(parent_type, field_node)
            super().handle_to_one_field(parent_type, field_node, related_field)

    def handle_to_many_field(
        self,
        parent_type: GraphQLObjectType,
        field_node: FieldNode,
        related_field: ToManyField,
    ) -> None:
        from django.contrib.contenttypes.fields import GenericRelation  # noqa: PLC0415

        name = get_related_field_name(related_field)
        alias = field_node.alias.value if field_node.alias else None
        data = self.optimization_data.add_prefetch_related(name, to_attr=alias)

        if isinstance(related_field, ManyToOneRel):
            data.only_fields.add(related_field.field.attname)

        elif isinstance(related_field, GenericRelation):
            data.only_fields.add(related_field.object_id_field_name)
            data.only_fields.add(related_field.content_type_field_name)

        self.handle_undine_field(parent_type, field_node)

        data.info = self.info
        with self.use_data(data):
            self.parse_filter_info(parent_type, field_node)
            super().handle_to_many_field(parent_type, field_node, related_field)

    def handle_generic_foreign_key(
        self,
        parent_type: GraphQLObjectType,
        field_node: FieldNode,
        related_field: GenericForeignKey,
    ) -> None:
        name = get_related_field_name(related_field)
        alias = field_node.alias.value if field_node.alias else None

        self.optimization_data.only_fields.add(related_field.ct_field)
        self.optimization_data.only_fields.add(related_field.fk_field)

        self.handle_undine_field(parent_type, field_node)

        # GenericForeignKey should contain a selection set
        if field_node.selection_set is None:  # pragma: no cover
            return

        for selection in field_node.selection_set.selections:
            if should_skip_node(selection, self.info.variable_values):
                continue

            # GenericForeignKey can only contain InlineFragments for its related models,
            # or the __typename metafield
            if not isinstance(selection, InlineFragmentNode):
                if is_typename_metafield(field_node):
                    self.handle_typename_metafield(parent_type, field_node)

                continue

            fragment_name = selection.type_condition.name.value
            fragment_type: GraphQLObjectType = self.info.schema.get_type(fragment_name)  # type: ignore[assignment]
            fragment_model = self.get_model(fragment_type)

            # Only optimize union types that are query typ
            if fragment_model is None:  # pragma: no cover
                continue

            data = self.optimization_data.add_generic_prefetch_related(name, fragment_model, to_attr=alias)
            data.info = self.info

            with self.use_data(data):
                query_type = get_undine_query_type(fragment_type)
                if query_type is not None:
                    self.handle_undine_query_type(query_type, {})

                if selection.selection_set is None:
                    continue

                with self.use_model(fragment_model):
                    self.handle_selections(fragment_type, selection.selection_set.selections)

    def handle_node_interface(self, parent_type: GraphQLInterfaceType, selections: Selections) -> None:
        # Node ID might not be selected, but we'll still fetch it.
        self.optimization_data.only_fields.add(self.model._meta.pk.name)  # type: ignore[union-attr]

    def handle_custom_field(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        self.handle_undine_field(parent_type, field_node)

    @contextmanager
    def use_data(self, nested_data: OptimizationData) -> Generator[None, Any, None]:
        original = self.optimization_data
        try:
            self.optimization_data = nested_data
            yield
        finally:
            self.optimization_data = original


@dataclasses.dataclass(slots=True)
class OptimizationData:
    """
    Holds QueryOptimizer optimization data. Can be processed to OptimizerResults
    when the optimization compilation is complete, which can then be used to optimize a queryset.
    """

    model: type[Model]
    info: GQLInfo

    parent: OptimizationData | None = None  # None if these are top-level optimizations.
    related_field: RelatedField | None = None  # Will be 'None' if there is no parent.

    only_fields: set[str] = dataclasses.field(default_factory=set)
    aliases: dict[str, DjangoExpression] = dataclasses.field(default_factory=dict)
    annotations: dict[str, DjangoExpression] = dataclasses.field(default_factory=dict)
    select_related: dict[str, OptimizationData] = dataclasses.field(default_factory=dict)
    prefetch_related: dict[str, OptimizationData] = dataclasses.field(default_factory=dict)
    generic_prefetches: dict[str, list[OptimizationData]] = dataclasses.field(default_factory=dict)

    filters: list[Q] = dataclasses.field(default_factory=list)
    order_by: list[OrderBy] = dataclasses.field(default_factory=list)
    distinct: bool = False
    none: bool = False
    pagination: PaginationHandler | None = None

    queryset_callback: QuerySetCallback = dataclasses.field(init=False)
    pre_filter_callback: FilterCallback | None = None
    post_filter_callback: FilterCallback | None = None
    field_calculations: list[Calculation] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        def default_queryset_callback(info: GQLInfo) -> QuerySet:
            return get_default_manager(self.model).get_queryset()  # type: ignore[arg-type,union-attr]

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

        field: ToOneField = self.model._meta.get_field(field_name)  # type: ignore[assignment,union-attr]
        model: type[Model] = field.related_model  # type: ignore[assignment]

        data = OptimizationData(model=model, info=self.info, related_field=field, parent=self)
        if query_type is not None:
            data.fill_from_query_type(query_type=query_type)

        self.select_related[field_name] = data

        # Fetch pk so that model is not "...both deferred and traversed using 'select_related' at the same time."
        data.only_fields.add(model._meta.pk.name)

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

        field: ToManyField = self.model._meta.get_field(field_name)  # type: ignore[assignment,union-attr]
        model: type[Model] = field.related_model  # type: ignore[assignment]

        data = OptimizationData(model=model, info=self.info, related_field=field, parent=self)
        if query_type is not None:
            data.fill_from_query_type(query_type=query_type)

        self.prefetch_related[name] = data
        return data

    def add_generic_prefetch_related(
        self,
        field_name: str,
        related_model: type[Model],
        *,
        query_type: type[QueryType] | None = None,
        to_attr: str | None = None,
    ) -> OptimizationData:
        """Add a 'prefetch_related' optimization for a generic prefetch for the given model."""
        field: ToManyField = self.model._meta.get_field(field_name)  # type: ignore[assignment,union-attr]

        name = to_attr or field_name
        prefetch_data: list[OptimizationData] = self.generic_prefetches.setdefault(name, [])

        data: OptimizationData | None = None

        if prefetch_data:
            data = next((o for o in prefetch_data if o.model == related_model), None)

        if data is None:
            data = OptimizationData(model=related_model, info=self.info, related_field=field, parent=self)
            prefetch_data.append(data)

        if query_type is not None:
            data.fill_from_query_type(query_type=query_type)

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

    def fill_from_query_type(self, query_type: type[QueryType]) -> OptimizationData:
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

    def process(self) -> OptimizationResults:
        """Process collected data to OptimizerResults that can be applied to a queryset."""
        results = OptimizationResults(
            related_field=self.related_field,
            only_fields=self.only_fields,
            aliases=self.aliases,
            annotations=self.annotations,
            filters=self.filters,
            order_by=self.order_by,
            distinct=self.distinct,
            none=self.none,
            pagination=self.pagination,
            pre_filter_callback=self.pre_filter_callback,
            post_filter_callback=self.post_filter_callback,
            field_calculations=self.field_calculations,
        )

        for select_related_data in self.select_related.values():
            # Check if we need to prefetch instead of joining.
            if select_related_data.should_promote_to_prefetch():
                prefetch = self._process_prefetch(select_related_data)
                results.prefetch_related.add(prefetch)
                continue

            # Otherwise extend lookups to this model.
            nested_results = select_related_data.process()
            results.extend(nested_results)

        for name, prefetch_related_data in self.prefetch_related.items():
            # Only need `to_attr` if it's different from the field name.
            to_attr: str | None = name
            if to_attr == prefetch_related_data.related_field.name:  # type: ignore[union-attr]
                to_attr = None

            prefetch = self._process_prefetch(prefetch_related_data, to_attr=to_attr)
            results.prefetch_related.add(prefetch)

        for name, generic_prefetches in self.generic_prefetches.items():
            if not generic_prefetches:
                continue

            # Only need `to_attr` if it's different from the field name.
            to_attr = name
            if to_attr == generic_prefetches[0].related_field.name:  # type: ignore[union-attr]
                to_attr = None

            generic_prefetch = self._process_generic_prefetch(generic_prefetches, to_attr=to_attr)
            results.prefetch_related.add(generic_prefetch)

        return results

    def _process_prefetch(self, data: OptimizationData, *, to_attr: str | None = None) -> Prefetch:
        """Process prefetch related optimization data to a Prefetch object."""
        optimizations = data.process()
        queryset = data.queryset_callback(data.info)  # type: ignore[arg-type]
        optimized_queryset = optimizations.apply(queryset, data.info)  # type: ignore[arg-type]

        field_name: str = data.related_field.name  # type: ignore[union-attr]
        return Prefetch(field_name, optimized_queryset, to_attr=to_attr)

    def _process_generic_prefetch(self, data: list[OptimizationData], *, to_attr: str | None = None) -> GenericPrefetch:
        """Process generic foreign key optimization data to a GenericPrefetch object."""
        optimized_querysets: list[QuerySet] = []

        for model_data in data:
            optimizations = model_data.process()
            queryset = model_data.queryset_callback(model_data.info)  # type: ignore[arg-type]
            optimized_queryset = optimizations.apply(queryset, model_data.info)  # type: ignore[arg-type]
            optimized_querysets.append(optimized_queryset)

        field_name: str = data[0].related_field.name  # type: ignore[union-attr]
        return GenericPrefetch(field_name, optimized_querysets, to_attr=to_attr)


@dataclasses.dataclass(slots=True)
class OptimizationResults:
    """Optimizations that can be applied to a queryset."""

    # The model field for a relation, if these are the results for a prefetch.
    related_field: RelatedField | None = None

    # Field optimizations
    only_fields: set[str] = dataclasses.field(default_factory=set)
    aliases: dict[str, DjangoExpression] = dataclasses.field(default_factory=dict)
    annotations: dict[str, DjangoExpression] = dataclasses.field(default_factory=dict)
    select_related: set[str] = dataclasses.field(default_factory=set)
    prefetch_related: set[Prefetch | str] = dataclasses.field(default_factory=set)

    # Filtering
    filters: list[Q] = dataclasses.field(default_factory=list)
    order_by: list[OrderBy] = dataclasses.field(default_factory=list)
    distinct: bool = False
    none: bool = False
    pagination: PaginationHandler | None = None

    pre_filter_callback: FilterCallback | None = None
    post_filter_callback: FilterCallback | None = None
    field_calculations: list[Calculation] = dataclasses.field(default_factory=list)

    def apply(self, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:  # noqa: C901, PLR0912
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

        for calculation in self.field_calculations:
            queryset = queryset.annotate(**{calculation.__field_name__: calculation(info)})

        for ftr in self.filters:
            queryset = queryset.filter(ftr)

        if self.post_filter_callback is not None:
            queryset = self.post_filter_callback(queryset, info)

        if self.pagination is not None:
            if self.related_field is None:
                queryset = self.pagination.paginate_queryset(queryset, info)
            else:
                queryset = self.pagination.paginate_prefetch_queryset(queryset, self.related_field, info)  # type: ignore[arg-type]

        return queryset

    def extend(self, other: OptimizationResults) -> OptimizationResults:
        """
        Extend the given optimization results to this one
        by prefixing their lookups using the other's `field_name`.
        """
        self.select_related.add(other.related_field.name)  # type: ignore[union-attr]
        self.only_fields.update(f"{other.related_field.name}{LOOKUP_SEP}{only}" for only in other.only_fields)  # type: ignore[union-attr]
        self.select_related.update(f"{other.related_field.name}{LOOKUP_SEP}{select}" for select in other.select_related)  # type: ignore[union-attr]

        for prefetch in other.prefetch_related:
            if isinstance(prefetch, str):
                self.prefetch_related.add(f"{other.related_field.name}{LOOKUP_SEP}{prefetch}")  # type: ignore[union-attr]
            if isinstance(prefetch, Prefetch):
                prefetch.add_prefix(other.related_field.name)  # type: ignore[union-attr]
                self.prefetch_related.add(prefetch)

        self.filters.extend(extend_expression(ftr, field_name=other.related_field.name) for ftr in other.filters)  # type: ignore[union-attr,misc]
        self.order_by.extend(extend_expression(order, field_name=other.related_field.name) for order in other.order_by)  # type: ignore[union-attr,misc]
        self.distinct |= other.distinct
        self.none |= other.none

        return self

    def __bool__(self) -> bool:
        return bool(self.only_fields or self.annotations or self.select_related or self.prefetch_related)
