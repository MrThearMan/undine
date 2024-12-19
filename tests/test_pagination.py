from __future__ import annotations

from typing import Any, NamedTuple

import pytest
from django.db import models

from tests.helpers import parametrize_helper
from undine.errors.exceptions import PaginationArgumentValidationError
from undine.relay import PaginationArgs, offset_to_cursor


class PaginationInput(NamedTuple):
    first: Any = None
    last: Any = None
    offset: Any = None
    after: Any = None
    before: Any = None
    max_limit: Any = None


class InputParams(NamedTuple):
    pagination_input: PaginationInput
    output: PaginationArgs | None
    errors: str | None


class DataParams(NamedTuple):
    pagination_args: PaginationArgs
    start: int
    stop: int


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "first": InputParams(
                pagination_input=PaginationInput(),
                output=PaginationArgs(
                    after=None,
                    before=None,
                    first=None,
                    last=None,
                    total_count=None,
                    max_limit=None,
                ),
                errors=None,
            ),
            "last": InputParams(
                pagination_input=PaginationInput(last=1),
                output=PaginationArgs(
                    after=None,
                    before=None,
                    first=None,
                    last=1,
                    total_count=None,
                    max_limit=None,
                ),
                errors=None,
            ),
            "offset": InputParams(
                pagination_input=PaginationInput(offset=1),
                output=PaginationArgs(
                    after=1,
                    before=None,
                    first=None,
                    last=None,
                    total_count=None,
                    max_limit=None,
                ),
                errors=None,
            ),
            "after": InputParams(
                pagination_input=PaginationInput(after=offset_to_cursor(0)),
                # Add 1 to after to make it exclusive in slicing.
                output=PaginationArgs(
                    after=1,
                    before=None,
                    first=None,
                    last=None,
                    total_count=None,
                    max_limit=None,
                ),
                errors=None,
            ),
            "before": InputParams(
                pagination_input=PaginationInput(before=offset_to_cursor(0)),
                output=PaginationArgs(
                    after=None,
                    before=0,
                    first=None,
                    last=None,
                    total_count=None,
                    max_limit=None,
                ),
                errors=None,
            ),
            "max limit": InputParams(
                pagination_input=PaginationInput(max_limit=1),
                output=PaginationArgs(
                    after=None,
                    before=None,
                    first=1,
                    last=None,
                    total_count=None,
                    max_limit=1,
                ),
                errors=None,
            ),
            "first zero": InputParams(
                pagination_input=PaginationInput(first=0),
                output=None,
                errors="Argument 'first' must be a positive integer.",
            ),
            "last zero": InputParams(
                pagination_input=PaginationInput(last=0),
                output=None,
                errors="Argument 'last' must be a positive integer.",
            ),
            "first negative": InputParams(
                pagination_input=PaginationInput(first=-1),
                output=None,
                errors="Argument 'first' must be a positive integer.",
            ),
            "last negative": InputParams(
                pagination_input=PaginationInput(last=-1),
                output=None,
                errors="Argument 'last' must be a positive integer.",
            ),
            "first exceeds max limit": InputParams(
                pagination_input=PaginationInput(first=2, max_limit=1),
                output=None,
                errors="Requesting first 2 records exceeds the limit of 1.",
            ),
            "last exceeds max limit": InputParams(
                pagination_input=PaginationInput(last=2, max_limit=1),
                output=None,
                errors="Requesting last 2 records exceeds the limit of 1.",
            ),
            "offset zero": InputParams(
                pagination_input=PaginationInput(offset=0),
                output=PaginationArgs(
                    after=None,
                    before=None,
                    first=None,
                    last=None,
                    total_count=None,
                    max_limit=None,
                ),
                errors=None,
            ),
            "after negative": InputParams(
                pagination_input=PaginationInput(after=offset_to_cursor(-1)),
                output=None,
                errors="The node pointed with `after` does not exist.",
            ),
            "before negative": InputParams(
                pagination_input=PaginationInput(before=offset_to_cursor(-1)),
                output=None,
                errors="The node pointed with `before` does not exist.",
            ),
            "after before": InputParams(
                pagination_input=PaginationInput(after=offset_to_cursor(1), before=offset_to_cursor(0), max_limit=None),
                output=None,
                errors="The node pointed with `after` must be before the node pointed with `before`.",
            ),
            "offset after": InputParams(
                pagination_input=PaginationInput(offset=1, after=offset_to_cursor(0)),
                output=None,
                errors="Can only use either `offset` or `before`/`after` for pagination.",
            ),
            "offset before": InputParams(
                pagination_input=PaginationInput(offset=1, before=offset_to_cursor(0)),
                output=None,
                errors="Can only use either `offset` or `before`/`after` for pagination.",
            ),
            "first not int": InputParams(
                pagination_input=PaginationInput(first="0"),
                output=None,
                errors="Argument 'first' must be a positive integer.",
            ),
            "last not int": InputParams(
                pagination_input=PaginationInput(last="0"),
                output=None,
                errors="Argument 'last' must be a positive integer.",
            ),
            "offset not int": InputParams(
                pagination_input=PaginationInput(offset="0"),
                output=None,
                errors="Argument `offset` must be a positive integer.",
            ),
            "max limit not int": InputParams(
                pagination_input=PaginationInput(max_limit="foo"),
                output=None,
                errors="Pagination max limit must be None or an integer, but got: 'foo'.",
            ),
        },
    ),
)
def test_pagination_args_from_connection_params(pagination_input, output, errors):
    try:
        args = PaginationArgs.from_connection_params(**pagination_input._asdict())
    except PaginationArgumentValidationError as error:
        if errors is None:
            pytest.fail(f"Unexpected error: {error}")
        assert str(error) == errors  # noqa: PT017
    else:
        if errors is not None:
            pytest.fail(f"Expected error: {errors}")
        assert args == output


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "default": DataParams(
                pagination_args=PaginationArgs(
                    first=None,
                    last=None,
                    after=None,
                    before=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=100,
            ),
            "after": DataParams(
                pagination_args=PaginationArgs(
                    after=1,
                    first=None,
                    before=None,
                    last=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=1,
                stop=100,
            ),
            "before": DataParams(
                pagination_args=PaginationArgs(
                    before=99,
                    first=None,
                    after=None,
                    last=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=99,
            ),
            "first": DataParams(
                pagination_args=PaginationArgs(
                    first=10,
                    last=None,
                    after=None,
                    before=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=10,
            ),
            "last": DataParams(
                pagination_args=PaginationArgs(
                    last=10,
                    first=None,
                    after=None,
                    before=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=90,
                stop=100,
            ),
            "after_before": DataParams(
                pagination_args=PaginationArgs(
                    after=1,
                    before=99,
                    first=None,
                    last=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=1,
                stop=99,
            ),
            "first_last": DataParams(
                pagination_args=PaginationArgs(
                    first=10,
                    last=8,
                    after=None,
                    before=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=2,
                stop=10,
            ),
            "after_before_first_last": DataParams(
                pagination_args=PaginationArgs(
                    after=1,
                    before=99,
                    first=10,
                    last=8,
                    max_limit=None,
                    total_count=100,
                ),
                start=3,
                stop=11,
            ),
            "after_bigger_than_total_count": DataParams(
                pagination_args=PaginationArgs(
                    after=101,
                    first=None,
                    before=None,
                    last=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=100,
                stop=100,
            ),
            "before_bigger_than_total_count": DataParams(
                pagination_args=PaginationArgs(
                    before=101,
                    first=None,
                    after=None,
                    last=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=100,
            ),
            "first_bigger_than_total_count": DataParams(
                pagination_args=PaginationArgs(
                    first=101,
                    last=None,
                    after=None,
                    before=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=100,
            ),
            "last_bigger_than_total_count": DataParams(
                pagination_args=PaginationArgs(
                    last=101,
                    first=None,
                    after=None,
                    before=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=100,
            ),
            "after_is_total_count": DataParams(
                pagination_args=PaginationArgs(
                    after=100,
                    first=None,
                    before=None,
                    last=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=100,
                stop=100,
            ),
            "before_is_total_count": DataParams(
                pagination_args=PaginationArgs(
                    before=100,
                    first=None,
                    after=None,
                    last=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=100,
            ),
            "first_is_total_count": DataParams(
                pagination_args=PaginationArgs(
                    first=100,
                    last=None,
                    after=None,
                    before=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=100,
            ),
            "last_is_total_count": DataParams(
                pagination_args=PaginationArgs(
                    last=100,
                    first=None,
                    after=None,
                    before=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=0,
                stop=100,
            ),
            "first_bigger_than_after_before": DataParams(
                pagination_args=PaginationArgs(
                    after=10,
                    before=20,
                    first=20,
                    last=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=10,
                stop=20,
            ),
            "last_bigger_than_after_before": DataParams(
                pagination_args=PaginationArgs(
                    after=10,
                    before=20,
                    last=20,
                    first=None,
                    max_limit=None,
                    total_count=100,
                ),
                start=10,
                stop=20,
            ),
        },
    ),
)
@pytest.mark.django_db
def test_calculate_queryset_slice(pagination_args: PaginationArgs, start: int, stop: int) -> None:
    queryset = pagination_args.paginate_queryset(models.QuerySet())
    assert queryset.query.low_mark == start
    assert queryset.query.high_mark == stop
