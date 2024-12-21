from __future__ import annotations

from typing import NamedTuple

import pytest
from django.db import models

from tests.helpers import parametrize_helper
from undine.errors.exceptions import PaginationArgumentValidationError
from undine.relay import PaginationArgs, offset_to_cursor
from undine.settings import undine_settings


class PaginationParams(NamedTuple):
    first: str | int | None = None
    last: str | int | None = None
    offset: str | int | None = None
    after: str | None = None
    before: str | None = None
    max_limit: str | int | None = 100


class InputParams(NamedTuple):
    params: PaginationParams
    start: int | None = None
    stop: int | None = None
    total_count: int | None = 200
    errors: str | None = None


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "none": InputParams(
                params=PaginationParams(),
                start=0,
                stop=100,
            ),
            "first": InputParams(
                params=PaginationParams(first=1),
                start=0,
                stop=1,
            ),
            "last": InputParams(
                params=PaginationParams(last=1),
                start=199,
                stop=200,
            ),
            "offset": InputParams(
                params=PaginationParams(offset=1),
                start=1,
                stop=101,
            ),
            "after": InputParams(
                params=PaginationParams(after=offset_to_cursor(0)),
                start=1,
                stop=101,
            ),
            "before": InputParams(
                params=PaginationParams(before=offset_to_cursor(10)),
                start=0,
                stop=10,
            ),
            "max limit": InputParams(
                params=PaginationParams(max_limit=1),
                start=0,
                stop=1,
            ),
            "after and before": InputParams(
                params=PaginationParams(after=offset_to_cursor(1), before=offset_to_cursor(99)),
                start=2,
                stop=99,
            ),
            "first and last": InputParams(
                params=PaginationParams(first=10, last=8),
                start=2,
                stop=10,
            ),
            "before and first": InputParams(
                params=PaginationParams(before=offset_to_cursor(50), first=10),
                start=0,
                stop=10,
            ),
            "before and last": InputParams(
                params=PaginationParams(before=offset_to_cursor(50), last=10),
                start=40,
                stop=50,
            ),
            "after and first": InputParams(
                params=PaginationParams(after=offset_to_cursor(50), first=10),
                start=51,
                stop=61,
            ),
            "after and last": InputParams(
                params=PaginationParams(after=offset_to_cursor(50), last=10),
                start=190,
                stop=200,
            ),
            "after and before and first": InputParams(
                params=PaginationParams(after=offset_to_cursor(1), before=offset_to_cursor(99), first=10),
                start=2,
                stop=12,
            ),
            "after and before and last": InputParams(
                params=PaginationParams(after=offset_to_cursor(1), before=offset_to_cursor(99), last=10),
                start=89,
                stop=99,
            ),
            "after and before and first and last": InputParams(
                params=PaginationParams(after=offset_to_cursor(1), before=offset_to_cursor(99), first=10, last=8),
                start=4,
                stop=12,
            ),
            "after bigger than total count": InputParams(
                params=PaginationParams(after=offset_to_cursor(201)),
                start=200,
                stop=200,
            ),
            "before bigger than total count": InputParams(
                params=PaginationParams(before=offset_to_cursor(201)),
                start=0,
                stop=100,
            ),
            "first bigger than interval from after to before": InputParams(
                params=PaginationParams(after=offset_to_cursor(9), before=offset_to_cursor(20), first=20),
                start=10,
                stop=20,
            ),
            "last bigger than interval from after to before": InputParams(
                params=PaginationParams(after=offset_to_cursor(9), before=offset_to_cursor(20), last=20),
                start=10,
                stop=20,
            ),
            "offset zero": InputParams(
                params=PaginationParams(offset=0),
                start=0,
                stop=100,
            ),
            "offset bigger than total count": InputParams(
                params=PaginationParams(offset=201),
                start=200,
                stop=200,
            ),
            "first zero": InputParams(
                params=PaginationParams(first=0),
                errors="Argument 'first' must be a positive integer.",
            ),
            "last zero": InputParams(
                params=PaginationParams(last=0),
                errors="Argument 'last' must be a positive integer.",
            ),
            "first negative": InputParams(
                params=PaginationParams(first=-1),
                errors="Argument 'first' must be a positive integer.",
            ),
            "last negative": InputParams(
                params=PaginationParams(last=-1),
                errors="Argument 'last' must be a positive integer.",
            ),
            "first exceeds max limit": InputParams(
                params=PaginationParams(first=2, max_limit=1),
                errors="Requesting first 2 records exceeds the limit of 1.",
            ),
            "last exceeds max limit": InputParams(
                params=PaginationParams(last=2, max_limit=1),
                errors="Requesting last 2 records exceeds the limit of 1.",
            ),
            "after negative": InputParams(
                params=PaginationParams(after=offset_to_cursor(-1)),
                errors="The node pointed with `after` does not exist.",
            ),
            "before negative": InputParams(
                params=PaginationParams(before=offset_to_cursor(-1)),
                errors="The node pointed with `before` does not exist.",
            ),
            "after bigger than before": InputParams(
                params=PaginationParams(after=offset_to_cursor(1), before=offset_to_cursor(0)),
                errors="The node pointed with `after` must be before the node pointed with `before`.",
            ),
            "offset after": InputParams(
                params=PaginationParams(offset=1, after=offset_to_cursor(0)),
                errors="Can only use either `offset` or `before`/`after` for pagination.",
            ),
            "offset before": InputParams(
                params=PaginationParams(offset=1, before=offset_to_cursor(10)),
                errors="Can only use either `offset` or `before`/`after` for pagination.",
            ),
            "first not int": InputParams(
                params=PaginationParams(first="0"),
                errors="Argument 'first' must be a positive integer.",
            ),
            "last not int": InputParams(
                params=PaginationParams(last="0"),
                errors="Argument 'last' must be a positive integer.",
            ),
            "offset not int": InputParams(
                params=PaginationParams(offset="0"),
                errors="Argument `offset` must be a positive integer.",
            ),
            "max limit not int": InputParams(
                params=PaginationParams(max_limit="foo"),
                errors="`max_limit` must be `None` or a positive integer, got: 'foo'",
            ),
            # TODO: `max_limit=None`.
            # TODO: `requires_total_count=True`.
            # TODO: `last=<int>` and `total_count=None`.
        },
    ),
)
@pytest.mark.django_db
def test_pagination_args__from_connection_params__paginate_queryset(params, start, stop, total_count, errors):
    try:
        args = PaginationArgs(**params._asdict())

    except PaginationArgumentValidationError as error:
        if errors is None:
            pytest.fail(f"Unexpected error: {error}")
        assert str(error) == errors  # noqa: PT017

    else:
        if errors is not None:
            pytest.fail(f"Expected error: {errors}")

        args.total_count = total_count

        queryset = args.paginate_queryset(models.QuerySet())
        assert queryset._hints[undine_settings.CONNECTION_TOTAL_COUNT_KEY] == total_count
        assert queryset._hints[undine_settings.CONNECTION_START_INDEX_KEY] == start
        assert queryset._hints[undine_settings.CONNECTION_STOP_INDEX_KEY] == stop


# TODO: test `paginate_prefetch_queryset`
