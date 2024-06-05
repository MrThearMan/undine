from __future__ import annotations

from typing import NamedTuple

import pytest
from django.db.models import Expression, Value
from django.db.models.expressions import F
from django.db.models.functions import Greatest

from example_project.app.models import Person, Task
from tests.factories import PersonFactory, TaskFactory
from tests.helpers import exact, mock_gql_info, parametrize_helper
from undine.exceptions import GraphQLPaginationArgumentValidationError
from undine.relay import PaginationHandler, offset_to_cursor
from undine.typing import ToManyField


class PaginationParams(NamedTuple):
    first: str | int | None = None
    last: str | int | None = None
    offset: str | int | None = None
    after: str | None = None
    before: str | None = None
    page_size: str | int | None = 100
    typename: str = "Test"


class InputParams(NamedTuple):
    params: PaginationParams
    start: int | Expression | None = None
    stop: int | Expression | None = None
    total_count: int | None = None


class ErrorParams(NamedTuple):
    params: PaginationParams
    errors: str | None = None


@pytest.mark.parametrize(
    **parametrize_helper({
        "none": InputParams(
            params=PaginationParams(),
            start=0,
            stop=100,
        ),
        "after": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 0)),
            start=1,
            stop=101,
        ),
        "before": InputParams(
            params=PaginationParams(before=offset_to_cursor("Test", 10)),
            start=0,
            stop=10,
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
            total_count=200,
        ),
        "offset": InputParams(
            params=PaginationParams(offset=1),
            start=1,
            stop=101,
        ),
        "max limit": InputParams(
            params=PaginationParams(page_size=1),
            start=0,
            stop=1,
        ),
        "after and before": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 1), before=offset_to_cursor("Test", 99)),
            start=2,
            stop=99,
        ),
        "first and last": InputParams(
            params=PaginationParams(first=10, last=8),
            start=2,
            stop=10,
        ),
        "before and first": InputParams(
            params=PaginationParams(before=offset_to_cursor("Test", 50), first=10),
            start=0,
            stop=10,
        ),
        "before and last": InputParams(
            params=PaginationParams(before=offset_to_cursor("Test", 50), last=10),
            start=40,
            stop=50,
        ),
        "after and first": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 50), first=10),
            start=51,
            stop=61,
        ),
        "after and last": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 50), last=10),
            start=190,
            stop=200,
            total_count=200,
        ),
        "after and before and first": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 1),
                before=offset_to_cursor("Test", 99),
                first=10,
            ),
            start=2,
            stop=12,
        ),
        "after and before and last": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 1),
                before=offset_to_cursor("Test", 99),
                last=10,
            ),
            start=89,
            stop=99,
        ),
        "after and before and first and last": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 1),
                before=offset_to_cursor("Test", 99),
                first=10,
                last=8,
            ),
            start=4,
            stop=12,
        ),
        "after bigger than total count": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 201)),
            start=202,
            stop=302,
            total_count=200,
        ),
        "before bigger than total count": InputParams(
            params=PaginationParams(before=offset_to_cursor("Test", 201)),
            start=0,
            stop=100,
        ),
        "first bigger than interval from after to before": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 9),
                before=offset_to_cursor("Test", 20),
                first=20,
            ),
            start=10,
            stop=20,
        ),
        "last bigger than interval from after to before": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 9),
                before=offset_to_cursor("Test", 20),
                last=20,
            ),
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
            total_count=200,
            start=201,
            stop=301,
        ),
    }),
)
@pytest.mark.django_db
def test_pagination_handler__paginate_queryset(params, start, stop, total_count, undine_settings) -> None:
    pagination = PaginationHandler(**params._asdict())

    pagination.total_count = total_count

    pagination.paginate_queryset(Task.objects.all(), mock_gql_info())

    assert pagination.total_count == total_count
    assert pagination.start == start
    assert pagination.stop == stop


@pytest.mark.parametrize(
    **parametrize_helper({
        "first zero": ErrorParams(
            params=PaginationParams(first=0),
            errors="Argument 'first' must be a positive integer.",
        ),
        "last zero": ErrorParams(
            params=PaginationParams(last=0),
            errors="Argument 'last' must be a positive integer.",
        ),
        "first negative": ErrorParams(
            params=PaginationParams(first=-1),
            errors="Argument 'first' must be a positive integer.",
        ),
        "last negative": ErrorParams(
            params=PaginationParams(last=-1),
            errors="Argument 'last' must be a positive integer.",
        ),
        "first exceeds max limit": ErrorParams(
            params=PaginationParams(first=2, page_size=1),
            errors="Requesting first 2 records exceeds the limit of 1.",
        ),
        "last exceeds max limit": ErrorParams(
            params=PaginationParams(last=2, page_size=1),
            errors="Requesting last 2 records exceeds the limit of 1.",
        ),
        "after negative": ErrorParams(
            params=PaginationParams(after=offset_to_cursor("Test", -1)),
            errors="The node pointed with `after` does not exist.",
        ),
        "before negative": ErrorParams(
            params=PaginationParams(before=offset_to_cursor("Test", -1)),
            errors="The node pointed with `before` does not exist.",
        ),
        "after bigger than before": ErrorParams(
            params=PaginationParams(after=offset_to_cursor("Test", 1), before=offset_to_cursor("Test", 0)),
            errors="The node pointed with `after` must be before the node pointed with `before`.",
        ),
        "offset after": ErrorParams(
            params=PaginationParams(offset=1, after=offset_to_cursor("Test", 0)),
            errors="Can only use either `offset` or `before`/`after` for pagination.",
        ),
        "offset before": ErrorParams(
            params=PaginationParams(offset=1, before=offset_to_cursor("Test", 10)),
            errors="Can only use either `offset` or `before`/`after` for pagination.",
        ),
        "first not int": ErrorParams(
            params=PaginationParams(first="0"),
            errors="Argument 'first' must be a positive integer.",
        ),
        "last not int": ErrorParams(
            params=PaginationParams(last="0"),
            errors="Argument 'last' must be a positive integer.",
        ),
        "offset not int": ErrorParams(
            params=PaginationParams(offset="0"),
            errors="Argument `offset` must be a positive integer.",
        ),
        "max limit not int": ErrorParams(
            params=PaginationParams(page_size="foo"),
            errors="`page_size` must be `None` or a positive integer, got: 'foo'",
        ),
        "after not a cursor": ErrorParams(
            params=PaginationParams(after="foo"),
            errors="Argument 'after' is not a valid cursor for type 'Test'.",
        ),
        "before not a cursor": ErrorParams(
            params=PaginationParams(before="foo"),
            errors="Argument 'before' is not a valid cursor for type 'Test'.",
        ),
        "after for different typename": ErrorParams(
            params=PaginationParams(after=offset_to_cursor("Foo", 10)),
            errors="Argument 'after' is not a valid cursor for type 'Test'.",
        ),
        "before for different typename": ErrorParams(
            params=PaginationParams(before=offset_to_cursor("Foo", 10)),
            errors="Argument 'before' is not a valid cursor for type 'Test'.",
        ),
    }),
)
def test_pagination_handler__validation_errors(params, errors, undine_settings) -> None:
    with pytest.raises(GraphQLPaginationArgumentValidationError, match=exact(errors)):
        PaginationHandler(**params._asdict())


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__requires_total_count(undine_settings) -> None:
    TaskFactory.create_batch(3)

    pagination = PaginationHandler(typename="A", page_size=100)
    pagination.requires_total_count = True
    pagination.paginate_queryset(Task.objects.all(), mock_gql_info())

    assert pagination.total_count == 3
    assert pagination.start == 0
    assert pagination.stop == 100


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__no_page_size(undine_settings) -> None:
    TaskFactory.create_batch(3)

    pagination = PaginationHandler(typename="A", page_size=None)
    pagination.paginate_queryset(Task.objects.all(), mock_gql_info())

    assert pagination.total_count is None
    assert pagination.start == 0
    assert pagination.stop is None


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__no_page_size__requires_total_count(undine_settings) -> None:
    TaskFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", page_size=None)
    pagination.requires_total_count = True
    pagination.paginate_queryset(Task.objects.all(), mock_gql_info())

    assert pagination.total_count == 3
    assert pagination.start == 0
    assert pagination.stop is None


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__no_page_size__filter_last(undine_settings) -> None:
    TaskFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", last=2, page_size=None)
    pagination.paginate_queryset(Task.objects.all(), mock_gql_info())

    assert pagination.total_count == 3
    assert pagination.start == 1
    assert pagination.stop == 3


@pytest.mark.parametrize(
    **parametrize_helper({
        "none": InputParams(
            params=PaginationParams(),
            start=0,
            stop=100,
        ),
        "after": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 0)),
            start=1,
            stop=101,
        ),
        "before": InputParams(
            params=PaginationParams(before=offset_to_cursor("Test", 10)),
            start=0,
            stop=10,
        ),
        "first": InputParams(
            params=PaginationParams(first=1),
            start=0,
            stop=1,
        ),
        # "last": Separate test below.
        "offset": InputParams(
            params=PaginationParams(offset=1),
            start=1,
            stop=101,
        ),
        "max limit": InputParams(
            params=PaginationParams(page_size=1),
            start=0,
            stop=1,
        ),
        "after and before": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 1), before=offset_to_cursor("Test", 99)),
            start=2,
            stop=99,
        ),
        "first and last": InputParams(
            params=PaginationParams(first=10, last=8),
            start=2,
            stop=10,
        ),
        "before and first": InputParams(
            params=PaginationParams(before=offset_to_cursor("Test", 50), first=10),
            start=0,
            stop=10,
        ),
        "before and last": InputParams(
            params=PaginationParams(before=offset_to_cursor("Test", 50), last=10),
            start=40,
            stop=50,
        ),
        "after and first": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 50), first=10),
            start=51,
            stop=61,
        ),
        # "after and last": Separate test below.
        "after and before and first": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 1),
                before=offset_to_cursor("Test", 99),
                first=10,
            ),
            start=2,
            stop=12,
        ),
        "after and before and last": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 1),
                before=offset_to_cursor("Test", 99),
                last=10,
            ),
            start=89,
            stop=99,
        ),
        "after and before and first and last": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 1),
                before=offset_to_cursor("Test", 99),
                first=10,
                last=8,
            ),
            start=4,
            stop=12,
        ),
        "after bigger than total count": InputParams(
            params=PaginationParams(after=offset_to_cursor("Test", 201)),
            start=202,
            stop=302,
        ),
        "before bigger than total count": InputParams(
            params=PaginationParams(before=offset_to_cursor("Test", 201)),
            start=0,
            stop=100,
        ),
        "first bigger than interval from after to before": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 9),
                before=offset_to_cursor("Test", 20),
                first=20,
            ),
            start=10,
            stop=20,
        ),
        "last bigger than interval from after to before": InputParams(
            params=PaginationParams(
                after=offset_to_cursor("Test", 9),
                before=offset_to_cursor("Test", 20),
                last=20,
            ),
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
            start=201,
            stop=301,
        ),
    }),
)
def test_pagination_handler__paginate_prefetch_queryset(params, start, stop, total_count, undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    pagination = PaginationHandler(**params._asdict())
    pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    assert pagination.total_count == total_count
    assert pagination.start == start
    assert pagination.stop == stop


def test_pagination_handler__paginate_prefetch_queryset__last(undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    pagination = PaginationHandler(typename="Test", last=2, page_size=100)
    pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    total_count = F(undine_settings.CONNECTION_TOTAL_COUNT_KEY)

    assert pagination.total_count == total_count
    assert str(pagination.start) == str(Greatest(total_count - Value(2), Value(0)))
    assert pagination.stop is None


def test_pagination_handler__paginate_prefetch_queryset__after_and_last(undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    pagination = PaginationHandler(typename="Test", after=offset_to_cursor("Test", 50), last=10, page_size=100)
    pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    total_count = F(undine_settings.CONNECTION_TOTAL_COUNT_KEY)

    assert pagination.total_count == total_count
    assert str(pagination.start) == str(Greatest(total_count - Value(10), Value(51)))
    assert pagination.stop is None


def test_pagination_handler__paginate_prefetch_queryset__requires_total_count(undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    pagination = PaginationHandler(typename="Test", page_size=100)
    pagination.requires_total_count = True
    pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    assert pagination.total_count == F(undine_settings.CONNECTION_TOTAL_COUNT_KEY)
    assert pagination.start == 0
    assert pagination.stop == 100


@pytest.mark.django_db
def test_pagination_handler__paginate_prefetch_queryset__no_page_size(undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    PersonFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", page_size=None)
    pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    assert pagination.total_count is None
    assert pagination.start == 0
    assert pagination.stop is None


@pytest.mark.django_db
def test_pagination_handler__paginate_prefetch_queryset__no_page_size__requires_total_count(undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    PersonFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", page_size=None)
    pagination.requires_total_count = True
    pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    assert pagination.total_count == F(undine_settings.CONNECTION_TOTAL_COUNT_KEY)
    assert pagination.start == 0
    assert pagination.stop is None


@pytest.mark.django_db
def test_pagination_handler__paginate_prefetch_queryset__no_page_size__last(undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    PersonFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", last=2, page_size=None)
    pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    total_count = F(undine_settings.CONNECTION_TOTAL_COUNT_KEY)

    assert pagination.total_count == total_count
    assert str(pagination.start) == str(Greatest(total_count - Value(2), Value(0)))
    assert pagination.stop is None
