from __future__ import annotations

from typing import Any, NamedTuple

import pytest
from graphql_relay import offset_to_cursor

from tests.helpers import parametrize_helper
from undine.dataclasses import PaginationArgs
from undine.errors.exceptions import PaginationArgumentValidationError
from undine.pagination import calculate_queryset_slice, validate_pagination_args


class PaginationInput(NamedTuple):
    first: Any = None
    last: Any = None
    offset: Any = None
    after: Any = None
    before: Any = None
    max_limit: Any = None


class InputParams(NamedTuple):
    pagination_input: PaginationInput
    output: PaginationArgs
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
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors=None,
            ),
            "last": InputParams(
                pagination_input=PaginationInput(last=1),
                output=PaginationArgs(after=None, before=None, first=None, last=1, size=None),
                errors=None,
            ),
            "offset": InputParams(
                pagination_input=PaginationInput(offset=1),
                output=PaginationArgs(after=1, before=None, first=None, last=None, size=None),
                errors=None,
            ),
            "after": InputParams(
                pagination_input=PaginationInput(after=offset_to_cursor(0)),
                # Add 1 to after to make it exclusive in slicing.
                output=PaginationArgs(after=1, before=None, first=None, last=None, size=None),
                errors=None,
            ),
            "before": InputParams(
                pagination_input=PaginationInput(before=offset_to_cursor(0)),
                output=PaginationArgs(after=None, before=0, first=None, last=None, size=None),
                errors=None,
            ),
            "max limit": InputParams(
                pagination_input=PaginationInput(max_limit=1),
                output=PaginationArgs(after=None, before=None, first=1, last=None, size=1),
                errors=None,
            ),
            "first zero": InputParams(
                pagination_input=PaginationInput(first=0),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Argument 'first' must be a positive integer.",
            ),
            "last zero": InputParams(
                pagination_input=PaginationInput(last=0),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Argument 'last' must be a positive integer.",
            ),
            "first negative": InputParams(
                pagination_input=PaginationInput(first=-1),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Argument 'first' must be a positive integer.",
            ),
            "last negative": InputParams(
                pagination_input=PaginationInput(last=-1),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Argument 'last' must be a positive integer.",
            ),
            "first exceeds max limit": InputParams(
                pagination_input=PaginationInput(first=2, max_limit=1),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Requesting first 2 records exceeds the limit of 1.",
            ),
            "last exceeds max limit": InputParams(
                pagination_input=PaginationInput(last=2, max_limit=1),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Requesting last 2 records exceeds the limit of 1.",
            ),
            "offset zero": InputParams(
                pagination_input=PaginationInput(offset=0),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors=None,
            ),
            "after negative": InputParams(
                pagination_input=PaginationInput(after=offset_to_cursor(-1)),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="The node pointed with `after` does not exist.",
            ),
            "before negative": InputParams(
                pagination_input=PaginationInput(before=offset_to_cursor(-1)),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="The node pointed with `before` does not exist.",
            ),
            "after before": InputParams(
                pagination_input=PaginationInput(after=offset_to_cursor(1), before=offset_to_cursor(0)),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="The node pointed with `after` must be before the node pointed with `before`.",
            ),
            "offset after": InputParams(
                pagination_input=PaginationInput(offset=1, after=offset_to_cursor(0)),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Can only use either `offset` or `before`/`after` for pagination.",
            ),
            "offset before": InputParams(
                pagination_input=PaginationInput(offset=1, before=offset_to_cursor(0)),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Can only use either `offset` or `before`/`after` for pagination.",
            ),
            "first not int": InputParams(
                pagination_input=PaginationInput(first="0"),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Argument 'first' must be a positive integer.",
            ),
            "last not int": InputParams(
                pagination_input=PaginationInput(last="0"),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Argument 'last' must be a positive integer.",
            ),
            "offset not int": InputParams(
                pagination_input=PaginationInput(offset="0"),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors="Argument `offset` must be a positive integer.",
            ),
            "max limit not int": InputParams(
                pagination_input=PaginationInput(max_limit="0"),
                output=PaginationArgs(after=None, before=None, first=None, last=None, size=None),
                errors=None,
            ),
        },
    ),
)
def test_validate_pagination_args(pagination_input, output, errors):
    try:
        args = validate_pagination_args(**pagination_input._asdict())
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
                pagination_args=PaginationArgs(size=100, first=None, last=None, after=None, before=None),
                start=0,
                stop=100,
            ),
            "after": DataParams(
                pagination_args=PaginationArgs(after=1, size=100, first=None, before=None, last=None),
                start=1,
                stop=100,
            ),
            "before": DataParams(
                pagination_args=PaginationArgs(before=99, size=100, first=None, after=None, last=None),
                start=0,
                stop=99,
            ),
            "first": DataParams(
                pagination_args=PaginationArgs(first=10, size=100, last=None, after=None, before=None),
                start=0,
                stop=10,
            ),
            "last": DataParams(
                pagination_args=PaginationArgs(last=10, size=100, first=None, after=None, before=None),
                start=90,
                stop=100,
            ),
            "after_before": DataParams(
                pagination_args=PaginationArgs(after=1, before=99, size=100, first=None, last=None),
                start=1,
                stop=99,
            ),
            "first_last": DataParams(
                pagination_args=PaginationArgs(first=10, last=8, size=100, after=None, before=None),
                start=2,
                stop=10,
            ),
            "after_before_first_last": DataParams(
                pagination_args=PaginationArgs(after=1, before=99, first=10, last=8, size=100),
                start=3,
                stop=11,
            ),
            "after_bigger_than_size": DataParams(
                pagination_args=PaginationArgs(after=101, size=100, first=None, before=None, last=None),
                start=100,
                stop=100,
            ),
            "before_bigger_than_size": DataParams(
                pagination_args=PaginationArgs(before=101, size=100, first=None, after=None, last=None),
                start=0,
                stop=100,
            ),
            "first_bigger_than_size": DataParams(
                pagination_args=PaginationArgs(first=101, size=100, last=None, after=None, before=None),
                start=0,
                stop=100,
            ),
            "last_bigger_than_size": DataParams(
                pagination_args=PaginationArgs(last=101, size=100, first=None, after=None, before=None),
                start=0,
                stop=100,
            ),
            "after_is_size": DataParams(
                pagination_args=PaginationArgs(after=100, size=100, first=None, before=None, last=None),
                start=100,
                stop=100,
            ),
            "before_is_size": DataParams(
                pagination_args=PaginationArgs(before=100, size=100, first=None, after=None, last=None),
                start=0,
                stop=100,
            ),
            "first_is_size": DataParams(
                pagination_args=PaginationArgs(first=100, size=100, last=None, after=None, before=None),
                start=0,
                stop=100,
            ),
            "last_is_size": DataParams(
                pagination_args=PaginationArgs(last=100, size=100, first=None, after=None, before=None),
                start=0,
                stop=100,
            ),
            "first_bigger_than_after_before": DataParams(
                pagination_args=PaginationArgs(after=10, before=20, first=20, size=100, last=None),
                start=10,
                stop=20,
            ),
            "last_bigger_than_after_before": DataParams(
                pagination_args=PaginationArgs(after=10, before=20, last=20, size=100, first=None),
                start=10,
                stop=20,
            ),
        },
    ),
)
def test_calculate_queryset_slice(pagination_args: PaginationArgs, start: int, stop: int) -> None:
    cut = calculate_queryset_slice(pagination_args)
    assert cut.start == start
    assert cut.stop == stop
