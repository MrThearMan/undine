from __future__ import annotations

from typing import TypedDict

from django.db import models
from graphql_relay import cursor_to_offset

from undine.errors import PaginationArgumentValidationError
from undine.settings import undine_settings


def calculate_queryset_slice(
    *,
    after: int | None,
    before: int | None,
    first: int | None,
    last: int | None,
    size: int,
) -> slice:
    """
    Calculate queryset slicing based on the provided arguments.
    Before this, the arguments should be validated so that:
     - `first` and `last`, positive integers or `None`
     - `after` and `before` are non-negative integers or `None`
     - If both `after` and `before` are given, `after` is less than or equal to `before`

    This function is based on the Relay pagination algorithm.
    See. https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm

    :param after: The index after which to start (exclusive).
    :param before: The index before which to stop (exclusive).
    :param first: The number of items to return from the start.
    :param last: The number of items to return from the end (after evaluating first).
    :param size: The total number of items in the queryset.
    """
    #
    # Start from form fetching max number of items.
    #
    start: int = 0
    stop: int = size
    #
    # If `after` is given, change the start index to `after`.
    # If `after` is greater than the current queryset size, change it to `size`.
    #
    if after is not None:
        start = min(after, stop)
    #
    # If `before` is given, change the stop index to `before`.
    # If `before` is greater than the current queryset size, change it to `size`.
    #
    if before is not None:
        stop = min(before, stop)
    #
    # If first is given, and it's smaller than the current queryset size,
    # change the stop index to `start + first`
    # -> Length becomes that of `first`, and the items after it have been removed.
    #
    if first is not None and first < (stop - start):
        stop = start + first
    #
    # If last is given, and it's smaller than the current queryset size,
    # change the start index to `stop - last`.
    # -> Length becomes that of `last`, and the items before it have been removed.
    #
    if last is not None and last < (stop - start):
        start = stop - last

    return slice(start, stop)


def calculate_slice_for_queryset(  # noqa: PLR0913
    queryset: models.QuerySet,
    *,
    after: int | None,
    before: int | None,
    first: int | None,
    last: int | None,
    size: int,
) -> models.QuerySet:
    """
    Annotate queryset with pagination slice start and stop indexes.
    This is the Django ORM equivalent of the `calculate_queryset_slice` function.
    """
    size_key = undine_settings.PREFETCH_COUNT_KEY
    # If the queryset has not been annotated with the total count, add an alias with the provided size.
    # (Since this is used in prefetch QuerySets, the provided size is likely wrong though.)
    if size_key not in queryset.query.annotations:  # pragma: no cover
        queryset = queryset.alias(**{size_key: models.Value(size)})

    start = models.Value(0)
    stop = models.F(undine_settings.PREFETCH_COUNT_KEY)

    if after is not None:
        start = models.Case(
            models.When(
                models.Q(**{f"{size_key}__lt": after}),
                then=stop,
            ),
            default=models.Value(after),
            output_field=models.IntegerField(),
        )

    if before is not None:
        stop = models.Case(
            models.When(
                models.Q(**{f"{size_key}__lt": before}),
                then=stop,
            ),
            default=models.Value(before),
            output_field=models.IntegerField(),
        )

    if first is not None:
        queryset = queryset.alias(**{f"{size_key}_size_1": stop - start})
        stop = models.Case(
            models.When(
                models.Q(**{f"{size_key}_size_1__lt": first}),
                then=stop,
            ),
            default=start + models.Value(first),
            output_field=models.IntegerField(),
        )

    if last is not None:
        queryset = queryset.alias(**{f"{size_key}_size_2": stop - start})
        start = models.Case(
            models.When(
                models.Q(**{f"{size_key}_size_2__lt": last}),
                then=start,
            ),
            default=stop - models.Value(last),
            output_field=models.IntegerField(),
        )

    return add_slice_to_queryset(queryset, start=start, stop=stop)


def add_slice_to_queryset(
    queryset: models.QuerySet,
    *,
    start: models.Expression,
    stop: models.Expression,
) -> models.QuerySet:
    return queryset.alias(
        **{
            undine_settings.PREFETCH_SLICE_START: start,
            undine_settings.PREFETCH_SLICE_STOP: stop,
        },
    )


class SubqueryCount(models.Subquery):
    template = "(SELECT COUNT(*) FROM (%(subquery)s) _count)"
    output_field = models.BigIntegerField()


class PaginationArgs(TypedDict):
    after: int | None
    before: int | None
    first: int | None
    last: int | None
    size: int | None


def validate_pagination_args(  # noqa: C901, PLR0912, PLR0913
    first: int | None,
    last: int | None,
    offset: int | None,
    after: str | None,
    before: str | None,
    max_limit: int | None = None,
) -> PaginationArgs:
    """
    Validate the pagination arguments and return a dictionary with the validated values.

    :param first: Number of records to return from the beginning.
    :param last: Number of records to return from the end.
    :param offset: Number of records to skip from the beginning.
    :param after: Cursor value for the last record in the previous page.
    :param before: Cursor value for the first record in the next page.
    :param max_limit: Maximum limit for the number of records that can be requested.
    """
    after = cursor_to_offset(after) if after is not None else None
    before = cursor_to_offset(before) if before is not None else None

    if first is not None:
        if not isinstance(first, int) or first <= 0:
            msg = "Argument 'first' must be a positive integer."
            raise PaginationArgumentValidationError(msg)

        if isinstance(max_limit, int) and first > max_limit:
            msg = f"Requesting first {first} records exceeds the limit of {max_limit}."
            raise PaginationArgumentValidationError(msg)

    if last is not None:
        if not isinstance(last, int) or last <= 0:
            msg = "Argument 'last' must be a positive integer."
            raise PaginationArgumentValidationError(msg)

        if isinstance(max_limit, int) and last > max_limit:
            msg = f"Requesting last {last} records exceeds the limit of {max_limit}."
            raise PaginationArgumentValidationError(msg)

    if isinstance(max_limit, int) and first is None and last is None:
        first = max_limit

    if offset is not None:
        if after is not None or before is not None:
            msg = "Can only use either `offset` or `before`/`after` for pagination."
            raise PaginationArgumentValidationError(msg)
        if not isinstance(offset, int) or offset < 0:
            msg = "Argument `offset` must be a positive integer."
            raise PaginationArgumentValidationError(msg)

        # Convert offset to after cursor value. Note that after cursor dictates
        # a value _after_ which results should be returned, so we need to subtract
        # 1 from the offset to get the correct cursor value.
        if offset > 0:  # ignore zero offset
            after = offset - 1

    if after is not None and (not isinstance(after, int) or after < 0):
        msg = "The node pointed with `after` does not exist."
        raise PaginationArgumentValidationError(msg)

    if before is not None and (not isinstance(before, int) or before < 0):
        msg = "The node pointed with `before` does not exist."
        raise PaginationArgumentValidationError(msg)

    if after is not None and before is not None and after >= before:
        msg = "The node pointed with `after` must be before the node pointed with `before`."
        raise PaginationArgumentValidationError(msg)

    # Since `after` is also exclusive, we need to add 1 to it, so that slicing works correctly.
    if after is not None:
        after += 1

    # Size is changed later with `queryset.count()`.
    size = max_limit if isinstance(max_limit, int) else None
    return PaginationArgs(after=after, before=before, first=first, last=last, size=size)
