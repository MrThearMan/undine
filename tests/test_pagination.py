from __future__ import annotations

from typing import NamedTuple

import pytest
from django.db.models import Expression, Value

from example_project.app.models import Person, Task
from tests.factories import PersonFactory, TaskFactory
from tests.helpers import exact, mock_gql_info, parametrize_helper
from undine.exceptions import GraphQLPaginationArgumentValidationError
from undine.pagination import OffsetPaginationHandler
from undine.typing import ToManyField


class PaginationParams(NamedTuple):
    offset: str | int | None = None
    limit: str | int | None = None
    page_size: str | int | None = 100


class InputParams(NamedTuple):
    params: PaginationParams
    start: int | Expression | None = None
    stop: int | Expression | None = None


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
        "offset": InputParams(
            params=PaginationParams(offset=1),
            start=1,
            stop=101,
        ),
        "limit": InputParams(
            params=PaginationParams(limit=1),
            start=0,
            stop=1,
        ),
        "page size": InputParams(
            params=PaginationParams(page_size=1),
            start=0,
            stop=1,
        ),
        "offset zero": InputParams(
            params=PaginationParams(offset=0),
            start=0,
            stop=100,
        ),
        "offset and limit": InputParams(
            params=PaginationParams(offset=1, limit=2),
            start=1,
            stop=3,
        ),
    }),
)
@pytest.mark.django_db
def test_pagination_handler__paginate_queryset(params, start, stop, undine_settings) -> None:
    pagination = OffsetPaginationHandler(**params._asdict())

    qs = pagination.paginate_queryset(Task.objects.all(), mock_gql_info())

    assert qs.query.low_mark == start
    assert qs.query.high_mark == stop


@pytest.mark.parametrize(
    **parametrize_helper({
        "limit exceeds page size": ErrorParams(
            params=PaginationParams(limit=2, page_size=1),
            errors="Requesting 2 records exceeds the maximum page size of 1.",
        ),
        "offset negative": ErrorParams(
            params=PaginationParams(offset=-1),
            errors="Argument `offset` must be a positive integer.",
        ),
        "offset not int": ErrorParams(
            params=PaginationParams(offset="0"),
            errors="Argument `offset` must be a positive integer.",
        ),
        "limit not int": ErrorParams(
            params=PaginationParams(limit="0"),
            errors="Argument `limit` must be a positive integer.",
        ),
        "page size not int": ErrorParams(
            params=PaginationParams(page_size="foo"),
            errors="`page_size` must be `None` or a positive integer, got: 'foo'",
        ),
    }),
)
def test_pagination_handler__validation_errors(params, errors, undine_settings) -> None:
    with pytest.raises(GraphQLPaginationArgumentValidationError, match=exact(errors)):
        OffsetPaginationHandler(**params._asdict())


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__no_page_size(undine_settings) -> None:
    TaskFactory.create_batch(3)

    pagination = OffsetPaginationHandler(page_size=None)
    qs = pagination.paginate_queryset(Task.objects.all(), mock_gql_info())

    assert qs.query.low_mark == 0
    assert qs.query.high_mark is None


@pytest.mark.parametrize(
    **parametrize_helper({
        "none": InputParams(
            params=PaginationParams(),
            start=0,
            stop=100,
        ),
        # "last": Separate test below.
        "offset": InputParams(
            params=PaginationParams(offset=1),
            start=1,
            stop=101,
        ),
        "page size": InputParams(
            params=PaginationParams(page_size=1),
            start=0,
            stop=1,
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
def test_pagination_handler__paginate_prefetch_queryset(params, start, stop, undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    pagination = OffsetPaginationHandler(**params._asdict())
    qs = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    assert qs.query.annotations[undine_settings.PAGINATION_START_INDEX_KEY] == Value(start)
    assert qs.query.annotations[undine_settings.PAGINATION_STOP_INDEX_KEY] == Value(stop)


@pytest.mark.django_db
def test_pagination_handler__paginate_prefetch_queryset__no_page_size(undine_settings) -> None:
    related_field: ToManyField = Task._meta.get_field("assignees")

    PersonFactory.create_batch(3)

    pagination = OffsetPaginationHandler(page_size=None)
    qs = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field, mock_gql_info())

    assert qs.query.low_mark == 0
    assert qs.query.high_mark is None
