from __future__ import annotations

from abc import ABC, abstractmethod
from copy import copy
from typing import TYPE_CHECKING

from django.db.models import F, ManyToManyField, ManyToManyRel, OuterRef, Value, Window
from django.db.models.functions import RowNumber

from undine import InterfaceType, QueryType, UnionType
from undine.exceptions import GraphQLPaginationArgumentValidationError
from undine.optimizer.prefetch_hack import register_for_prefetch_hack
from undine.settings import undine_settings
from undine.utils.model_utils import SubqueryCount
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from undine import GQLInfo
    from undine.optimizer import OptimizationData
    from undine.typing import CombinableExpression, ToManyField


__all__ = [
    "OffsetPagination",
    "OffsetPaginationHandler",
    "PaginationHandler",
]


class PaginationHandler(ABC):
    """Base class for all pagination handlers."""

    @abstractmethod
    def paginate_queryset(self, queryset: QuerySet, info: GQLInfo) -> QuerySet: ...

    @abstractmethod
    def paginate_prefetch_queryset(self, queryset: QuerySet, field: ToManyField, info: GQLInfo) -> QuerySet: ...

    @abstractmethod
    def optimize(self, optimization_data: OptimizationData, info: GQLInfo) -> None: ...


class OffsetPaginationHandler(PaginationHandler):
    """Paginate a queryset using offset and limit."""

    def __init__(self, *, offset: int | None = None, limit: int | None = None, page_size: int | None = None) -> None:
        """
        Create a new OffsetPaginationHandler.

        :param offset: Number of item to skip from the start. No offset if `None`.
        :param limit: Maximum limit for the number of item that can be requested in a page. No limit if `None`.
        :param page_size: Maximum limit for the number of item that can be requested in a page. No limit if `None`.
        """
        self.offset: int = offset if offset is not None else 0
        self.limit: int | None = limit if limit is not None else page_size

        self.validate_arguments(offset=offset, limit=limit, page_size=page_size)

    def validate_arguments(self, *, offset: int | None, limit: int | None, page_size: int | None) -> None:
        validate_offset(offset=offset)
        validate_page_size(page_size=page_size)
        validate_limit(limit=limit, page_size=page_size)

    def paginate_queryset(self, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        """Paginate a top-level queryset."""
        if self.limit is None:
            return queryset[self.offset :]
        return queryset[self.offset : self.offset + self.limit]

    def paginate_prefetch_queryset(self, queryset: QuerySet, field: ToManyField, info: GQLInfo) -> QuerySet:
        """
        Paginate a prefetch queryset.

        Uses a window function partitioned by the given related field.

        Pagination arguments are annotated to the queryset, since they are calculated in the database.
        There is the issue that they might not be available if the queryset is empty after pagination,
        but since they can be different for each prefetch partition, we cannot do anything about that.
        """
        if isinstance(field, ManyToManyField | ManyToManyRel):
            register_for_prefetch_hack(queryset, field)

        related_name = field.remote_field.name

        queryset = _add_total_count(queryset, related_name)

        queryset = _add_partition_index(queryset, related_name)

        queryset = _add_start_index(queryset, self.offset)
        queryset = _filter_by_start_index(queryset)

        if self.limit is not None:
            queryset = _add_stop_index(queryset, self.offset + self.limit)
            queryset = _filter_by_stop_index(queryset)

        return queryset

    def optimize(self, optimization_data: OptimizationData, info: GQLInfo) -> None: ...


class OffsetPagination:
    """A wrapper for paginating a `QueryType` using offset and limit."""

    def __init__(
        self,
        ref: type[QueryType | UnionType | InterfaceType],
        /,
        *,
        page_size: int | None = undine_settings.PAGINATION_PAGE_SIZE,
        pagination_handler: type[OffsetPaginationHandler] = OffsetPaginationHandler,
        description: str | None = None,
    ) -> None:
        """
        Create a new OffsetPagination.

        :param ref: The `QueryType`, `UnionType`, or `InterfaceType` to paginate.
        :param page_size: Maximum number of items to return in a page. No limit if `None`.
        :param pagination_handler: Handler to use for pagination.
        :param description: Description for the created GraphQL type.
        """
        self.query_type = ref if is_subclass(ref, QueryType) else None
        self.union_type = ref if is_subclass(ref, UnionType) else None
        self.interface_type = ref if is_subclass(ref, InterfaceType) else None

        self.page_size = page_size
        self.pagination_handler = pagination_handler
        self.description = description


def _add_partition_index(queryset: QuerySet, related_name: str) -> QuerySet:
    """Add an index to each instance in the queryset, partitioned by the given related name."""
    return queryset.alias(
        **{
            undine_settings.PAGINATION_INDEX_KEY: (
                Window(
                    expression=RowNumber(),
                    partition_by=F(related_name),
                    order_by=queryset.query.order_by or copy(queryset.model._meta.ordering) or None,  # type: ignore[arg-type]
                )
                - Value(1)  # Start from zero.
            ),
        },
    )


def _add_total_count(queryset: QuerySet, related_name: str) -> QuerySet:
    """Add an annotation to the given queryset with the total count of objects in the queryset."""
    total_count = _total_count_subquery(queryset, related_name)
    return queryset.annotate(**{undine_settings.PAGINATION_TOTAL_COUNT_KEY: total_count})


def _total_count_subquery(queryset: QuerySet, related_name: str) -> SubqueryCount:
    """Get a subquery for calculating total count, partitioned by the given related name."""
    return SubqueryCount(queryset=queryset.filter(**{related_name: OuterRef(related_name)}))


def _add_start_index(queryset: QuerySet, start: int | CombinableExpression) -> QuerySet:
    """Add an annotation to the given queryset with the start index of the current page."""
    if isinstance(start, int):
        start = Value(start)
    return queryset.annotate(**{undine_settings.PAGINATION_START_INDEX_KEY: start})


def _filter_by_start_index(queryset: QuerySet) -> QuerySet:
    """Filter out all items before the start index of the current page."""
    start = F(undine_settings.PAGINATION_START_INDEX_KEY)
    return queryset.filter(**{f"{undine_settings.PAGINATION_INDEX_KEY}__gte": start})


def _add_stop_index(queryset: QuerySet, stop: int | CombinableExpression) -> QuerySet:
    """Add an annotation to the given queryset with the stop index of the current page."""
    if isinstance(stop, int):  # pragma: no branch
        stop = Value(stop)
    return queryset.annotate(**{undine_settings.PAGINATION_STOP_INDEX_KEY: stop})


def _filter_by_stop_index(queryset: QuerySet) -> QuerySet:
    """Filter out all items on or after the stop index of the current page."""
    stop = F(undine_settings.PAGINATION_STOP_INDEX_KEY)
    return queryset.filter(**{f"{undine_settings.PAGINATION_INDEX_KEY}__lt": stop})


def validate_page_size(*, page_size: int | None) -> None:
    if page_size is None:
        return

    if not isinstance(page_size, int) or page_size < 1:
        msg = f"`page_size` must be `None` or a positive integer, got: {page_size!r}"
        raise GraphQLPaginationArgumentValidationError(msg)


def validate_offset(*, offset: int | None) -> None:
    if offset is None:
        return

    if not isinstance(offset, int) or offset < 0:
        msg = "Argument `offset` must be a positive integer."
        raise GraphQLPaginationArgumentValidationError(msg)


def validate_limit(*, limit: int | None, page_size: int | None) -> None:
    if limit is None:
        return

    if not isinstance(limit, int) or limit < 0:
        msg = "Argument `limit` must be a positive integer."
        raise GraphQLPaginationArgumentValidationError(msg)

    if isinstance(page_size, int) and limit > page_size:
        msg = f"Requesting {limit} records exceeds the maximum page size of {page_size}."
        raise GraphQLPaginationArgumentValidationError(msg)
