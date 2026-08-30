from __future__ import annotations

import dataclasses
import inspect
import uuid
from collections import defaultdict
from copy import copy
from itertools import count
from typing import TYPE_CHECKING, Any, Literal

from asgiref.sync import sync_to_async
from django.db.models import CharField, F, OrderBy, Q, Value, Window
from django.db.models.functions import RowNumber

from undine.dataclasses import PaginationPage
from undine.optimizer.prefetch_hack import evaluate_with_prefetch_hack_async, evaluate_with_prefetch_hack_sync
from undine.relay.cursors import (
    OrderingDescriptor,
    build_keyset_filter,
    decode_cursor_payload,
    encode_cursor,
    order_by_list_to_ordering_descriptors,
    parse_cursor_values,
)
from undine.settings import undine_settings
from undine.typing import ConnectionDict, NodeDict, PageInfoDict
from undine.utils.graphql.utils import get_arguments
from undine.utils.model_utils import create_union_queryset

from .limits import entrypoint_limit, offset_pagination_handler

if TYPE_CHECKING:
    from collections.abc import Hashable, Iterable

    from django.db.models import Model, QuerySet

    from undine import Entrypoint, FilterSet, OrderSet, QueryType
    from undine.optimizer.optimizer import OptimizationResults
    from undine.relay import CursorPaginationHandler
    from undine.typing import GQLInfo


__all__ = [
    "UnionMembers",
    "UnionOrdering",
    "apply_shared_filters",
    "apply_shared_order",
    "apply_union_cursor_filters",
    "check_permissions",
    "check_permissions_async",
    "connection_from_page",
    "empty_connection",
    "fetch_union_instances",
    "fetch_union_instances_async",
    "limit_union_query",
    "optimize_members",
    "union_count",
    "union_count_async",
    "union_page",
    "union_page_query",
]


# Members


@dataclasses.dataclass(frozen=True, slots=True)
class UnionMembers:
    """The optimized queryset of each query type the current query selects something from."""

    querysets: dict[type[QueryType], QuerySet] = dataclasses.field(default_factory=dict)
    """Querysets for each QueryType in the union."""

    query_types: dict[str, type[QueryType]] = dataclasses.field(default_factory=dict)
    """The same query types as `querysets` is keyed by, indexed by schema name to look one up from a row."""

    descriptors: dict[str, list[OrderingDescriptor]] = dataclasses.field(default_factory=dict)
    """Each member's own ordering descriptors, keyed by schema name. Only built when asked for."""

    def __bool__(self) -> bool:
        return bool(self.querysets)


def optimize_members(
    query_types: Iterable[type[QueryType]],
    info: GQLInfo,
    *,
    build_descriptors: bool,
    **kwargs: Any,
) -> UnionMembers:
    """
    Build a queryset for each member the current query selects something from.

    :param build_descriptors: Also describe each member's own ordering. Needed for cursors.
                              This annotates the columns an expression order is read and compared
                              under, so it can only be done before the optimizations are applied.
    """
    members = UnionMembers()

    for query_type in query_types:
        optimizations = optimize_member(query_type, info, **kwargs)
        if optimizations is None:
            continue

        if build_descriptors:
            descriptors = order_by_list_to_ordering_descriptors(
                optimizations.order_by,
                model=query_type.__model__,
                annotations=optimizations.annotations,
                only_fields=optimizations.only_fields,
            )
            members.descriptors[query_type.__schema_name__] = descriptors

        queryset = query_type.__get_queryset__(info)
        members.querysets[query_type] = optimizations.apply(queryset, info)
        members.query_types[query_type.__schema_name__] = query_type

    return members


def optimize_member(query_type: type[QueryType], info: GQLInfo, **kwargs: Any) -> OptimizationResults | None:
    """Returns `None` if the query selects nothing from this member."""
    model = query_type.__model__

    argument_values: dict[str, Any] = {}
    filter_key = f"{undine_settings.QUERY_TYPE_FILTER_INPUT_KEY}{model.__name__}"
    order_by_key = f"{undine_settings.QUERY_TYPE_ORDER_INPUT_KEY}{model.__name__}"

    if filter_key in kwargs:
        argument_values[undine_settings.QUERY_TYPE_FILTER_INPUT_KEY] = kwargs[filter_key]
    if order_by_key in kwargs:
        argument_values[undine_settings.QUERY_TYPE_ORDER_INPUT_KEY] = kwargs[order_by_key]

    optimizer = undine_settings.OPTIMIZER_CLASS(model=model, info=info)
    optimizer.handle_undine_query_type(query_type, argument_values)
    optimizations = optimizer.compile()

    if optimizations.nothing_selected:
        return None

    primary_key_order = OrderBy(F("pk"))
    optimizations.order_by.append(primary_key_order)

    optimizations.annotations["__typename"] = Value(query_type.__schema_name__)

    # The union query can only order by columns every member shares, so this member's own
    # ordering is reduced to a rank the union can order by. See `UnionOrdering`.
    own_order_by = copy(optimizations.order_by)
    rank = Window(expression=RowNumber(), order_by=own_order_by)
    optimizations.annotations[undine_settings.PAGINATION_MEMBER_RANK_KEY] = rank

    # Limiting and pagination apply to the combined result, not to a single member.
    optimizations.pagination = None

    return optimizations


# Shared filtering and ordering


def apply_shared_filters(filterset: type[FilterSet] | None, members: UnionMembers, info: GQLInfo) -> bool:
    """Returns `False` if the filtering cannot match anything, in which case the result is empty."""
    if not filterset:
        return True

    arguments = get_arguments(info)
    filter_data = arguments.get(undine_settings.QUERY_TYPE_FILTER_INPUT_KEY, {})

    results = filterset.__build__(filter_data, info)
    if results.none:
        return False

    for query_type, queryset in members.querysets.items():
        if results.aliases:
            queryset = queryset.alias(**results.aliases)  # noqa: PLW2901
        if results.distinct:
            queryset = queryset.distinct()  # noqa: PLW2901
        if results.filters:
            condition = Q(*results.filters)
            queryset = queryset.filter(condition)  # noqa: PLW2901

        members.querysets[query_type] = queryset

    return True


def apply_shared_order(orderset: type[OrderSet] | None, members: UnionMembers, info: GQLInfo) -> UnionOrdering:
    shared: list[OrderingDescriptor] = []
    annotations: dict[str, Any] = {}

    if orderset:
        arguments = get_arguments(info)
        order_data = arguments.get(undine_settings.QUERY_TYPE_ORDER_INPUT_KEY, [])

        results = orderset.__build__(order_data, info)

        for query_type, queryset in members.querysets.items():
            if results.aliases:
                queryset = queryset.alias(**results.aliases)  # noqa: PLW2901
            if results.order_by:
                queryset = queryset.order_by(*results.order_by, *queryset.query.order_by)  # noqa: PLW2901

            members.querysets[query_type] = queryset

        # The shared order set spans all members, so any of their models describes it.
        first_query_type = next(iter(members.querysets))
        shared = order_by_list_to_ordering_descriptors(
            results.order_by,
            model=first_query_type.__model__,
            annotations=annotations,
            only_fields=set(),
        )

        # An expression order is read and compared under the column it was annotated as,
        # so every member has to carry that column.
        for query_type, queryset in members.querysets.items():
            members.querysets[query_type] = queryset.annotate(**annotations)

    # Rows of different members that tie on the shared ordering are separated by type,
    # so that each member's own ordering only has to break ties within that type.
    typename_descriptor = OrderingDescriptor(
        attname="__typename",
        order_by=OrderBy(F("__typename")),
        output_field=CharField(),
        maybe_null=False,
    )
    shared.append(typename_descriptor)

    return UnionOrdering(shared=shared, per_typename=members.descriptors)


@dataclasses.dataclass(frozen=True, slots=True)
class UnionOrdering:
    """
    How the member querysets are ordered once they are combined into a single union query.

    The ordering is a shared prefix followed by a per-member tail. Only the prefix can be an
    `ORDER BY` column of the union query: each member can order by its own fields, of its own
    types, while the union projection has one column per position. The tail is therefore reduced to a
    single integer rank per member, which the union orders by last. Since the shared prefix
    ends with `__typename`, every row that reaches the rank comes from the same member, so
    ranking within a member orders those rows exactly as that member asked for.

    A cursor holds the shared values followed by the values of the member the row came from.
    The rank cannot go in a cursor, because it shifts when rows are added or removed between pages.
    """

    shared: list[OrderingDescriptor]
    per_typename: dict[str, list[OrderingDescriptor]]

    def expressions(self) -> list[Any]:
        """The `ORDER BY` of the union query."""
        # `descriptor.order_by` cannot be reused as-is. For an expression or related field order it
        # still refers to the original expression, while a cursor is compared against the column
        # that expression was annotated under. Order by that column so the two agree.
        order_by: list[Any] = [
            OrderBy(
                F(descriptor.attname),
                descending=descriptor.order_by.descending,
                nulls_first=descriptor.order_by.nulls_first,
                nulls_last=descriptor.order_by.nulls_last,
            )
            for descriptor in self.shared
        ]
        order_by.append(undine_settings.PAGINATION_MEMBER_RANK_KEY)
        return order_by

    def for_row(self, typename: str) -> list[OrderingDescriptor]:
        own_descriptors = self.per_typename.get(typename, [])
        return [*self.shared, *own_descriptors]

    def for_member(self, *, cursor_typename: str, member_typename: str) -> list[OrderingDescriptor]:
        """
        The descriptors a cursor is compared against when filtering one member's queryset.

        The per-member tail only applies when the cursor points to a row of that same member.
        For any other member `__typename` differs, so the shared prefix already decides which
        side of the cursor every one of its rows is on.
        """
        if cursor_typename == member_typename:
            return self.for_row(cursor_typename)
        return self.shared


# Union query


def union_page_query(members: UnionMembers, ordering: UnionOrdering) -> QuerySet:
    """Combine the member querysets into a single ordered query of `(__typename, pk)` rows."""
    union_queryset = create_union_queryset(members.querysets.values())

    expressions = ordering.expressions()
    union_queryset = union_queryset.order_by(*expressions)

    return union_queryset.values("__typename", "pk")


def limit_union_query(union_queryset: QuerySet, entrypoint: Entrypoint, info: GQLInfo) -> QuerySet:
    """
    Limit the union query to the page the entrypoint asks for.

    An offset paginated entrypoint pages with the `offset` and `limit` arguments the client gave it.
    Any other entrypoint is capped at its own limit.
    """
    pagination = offset_pagination_handler(entrypoint, info)
    if pagination is not None:
        return pagination.paginate_queryset(union_queryset, info)

    limit = entrypoint_limit(entrypoint)
    if limit is None:
        return union_queryset

    return union_queryset[:limit]


def union_count(members: UnionMembers) -> int:
    count_queryset = union_count_query(members)
    return count_queryset.count()


async def union_count_async(members: UnionMembers) -> int:
    count_queryset = union_count_query(members)
    count = sync_to_async(count_queryset.count)
    return await count()


def union_count_query(members: UnionMembers) -> QuerySet:
    identities = [queryset.values("__typename", "pk") for queryset in members.querysets.values()]
    return create_union_queryset(identities)


def apply_union_cursor_filters(
    members: UnionMembers,
    ordering: UnionOrdering,
    pagination: CursorPaginationHandler,
) -> None:
    """
    The cursor filters are applied to each member separately, since Django does not support
    calling `filter()` on a queryset that has already been combined with `union()`.
    """
    kinds: tuple[Literal["after", "before"], ...] = ("after", "before")

    for kind in kinds:
        cursor: str | None = getattr(pagination, kind)
        if cursor is None:
            continue

        string_values = decode_cursor_payload(cursor, typename=pagination.typename, kind=kind)

        # A cursor built for a different ordering may not name a member at all.
        # It then matches none of them, and `parse_cursor_values` rejects it below.
        cursor_typename = string_values.get("__typename") or ""

        cursor_descriptors = ordering.for_row(cursor_typename)
        values = parse_cursor_values(
            string_values,
            descriptors=cursor_descriptors,
            typename=pagination.typename,
            kind=kind,
        )

        for query_type, queryset in members.querysets.items():
            descriptors = ordering.for_member(
                cursor_typename=cursor_typename,
                member_typename=query_type.__schema_name__,
            )
            condition = build_keyset_filter(descriptors, values, before=kind == "before")
            members.querysets[query_type] = queryset.filter(condition)


def fetch_union_instances(members: UnionMembers, union_queryset: QuerySet) -> list[Model]:
    """
    Fetch the instances the given union query selected, in the order it returned them.

    The union query can only project columns every member shares, so it selects identity only.
    The instances themselves are fetched per member, and put back into that order.
    """
    indexes_by_typename: dict[str, dict[Hashable, int]] = defaultdict(dict)

    for index, row in enumerate(union_queryset):
        primary_key = coalesce_primary_key(row["pk"])
        indexes_by_typename[row["__typename"]][primary_key] = index

    instances_by_index: dict[int, Model] = {}

    for typename, indexes_by_primary_key in indexes_by_typename.items():
        query_type = members.query_types[typename]
        primary_keys = list(indexes_by_primary_key)
        queryset = members.querysets[query_type].filter(pk__in=primary_keys)

        instances = evaluate_with_prefetch_hack_sync(queryset)
        for instance in instances:
            primary_key = coalesce_primary_key(instance.pk)
            instances_by_index[indexes_by_primary_key[primary_key]] = instance

    sorted_instances = sorted(instances_by_index.items())
    return [instance for _, instance in sorted_instances]


async def fetch_union_instances_async(members: UnionMembers, union_queryset: QuerySet) -> list[Model]:
    indexes_by_typename: dict[str, dict[Hashable, int]] = defaultdict(dict)
    counter = count()

    async for row in union_queryset:
        primary_key = coalesce_primary_key(row["pk"])
        indexes_by_typename[row["__typename"]][primary_key] = next(counter)

    instances_by_index: dict[int, Model] = {}

    for typename, indexes_by_primary_key in indexes_by_typename.items():
        query_type = members.query_types[typename]
        primary_keys = list(indexes_by_primary_key)
        queryset = members.querysets[query_type].filter(pk__in=primary_keys)

        instances = await evaluate_with_prefetch_hack_async(queryset)
        for instance in instances:
            primary_key = coalesce_primary_key(instance.pk)
            instances_by_index[indexes_by_primary_key[primary_key]] = instance

    sorted_instances = sorted(instances_by_index.items())
    return [instance for _, instance in sorted_instances]


def coalesce_primary_key(value: Any) -> Any:
    # Converting UUIDs to hex avoids an issue with union querysets with mixed int and UUID pks.
    return value.hex if isinstance(value, uuid.UUID) else value


# Permissions


def check_permissions(
    *,
    entrypoint: Entrypoint,
    root: Any,
    info: GQLInfo,
    members: UnionMembers,
    instances: list[Model],
) -> None:
    for instance in instances:
        if entrypoint.permissions_func is not None:
            entrypoint.permissions_func(root, info, instance)
        else:
            typename = getattr(instance, "__typename")
            query_type = members.query_types[typename]
            query_type.__permissions__(instance, info)


async def check_permissions_async(
    *,
    entrypoint: Entrypoint,
    root: Any,
    info: GQLInfo,
    members: UnionMembers,
    instances: list[Model],
) -> None:
    for instance in instances:
        if entrypoint.permissions_func is not None:
            if inspect.iscoroutinefunction(entrypoint.permissions_func):
                await entrypoint.permissions_func(root, info, instance)
            else:
                entrypoint.permissions_func(root, info, instance)

        else:
            typename = getattr(instance, "__typename")
            query_type = members.query_types[typename]

            if inspect.iscoroutinefunction(query_type.__permissions__):
                await query_type.__permissions__(instance, info)
            else:
                query_type.__permissions__(instance, info)


# Connection results


def union_page(
    instances: list[Model],
    pagination: CursorPaginationHandler,
    ordering: UnionOrdering,
) -> PaginationPage[Model]:
    """Cut the fetched rows down to the requested page and build a cursor for each row in it."""
    cut = pagination.cut_to_page(instances)
    cursors: list[str] = []

    for instance in cut.instances:
        typename = getattr(instance, "__typename")
        descriptors = ordering.for_row(typename)
        cursor = encode_cursor(instance, typename=pagination.typename, descriptors=descriptors)
        cursors.append(cursor)

    return PaginationPage(
        instances=cut.instances,
        cursors=cursors,
        total_count=pagination.total_count or 0,
        has_next_page=cut.has_next_page,
        has_previous_page=cut.has_previous_page,
    )


def connection_from_page(page: PaginationPage[Model]) -> ConnectionDict[Model]:
    rows = zip(page.cursors, page.instances, strict=True)
    edges = [NodeDict(cursor=cursor, node=instance) for cursor, instance in rows]
    page_info = PageInfoDict(
        hasNextPage=page.has_next_page,
        hasPreviousPage=page.has_previous_page,
        startCursor=None if not edges else edges[0]["cursor"],
        endCursor=None if not edges else edges[-1]["cursor"],
    )
    return ConnectionDict(totalCount=page.total_count, pageInfo=page_info, edges=edges)


def empty_connection() -> ConnectionDict[Model]:
    page_info = PageInfoDict(hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None)
    return ConnectionDict(totalCount=0, pageInfo=page_info, edges=[])
