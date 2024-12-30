from __future__ import annotations

from typing import NamedTuple

import pytest
from django.db.models import Expression, Value
from django.db.models.expressions import CombinedExpression
from django.db.models.functions import Greatest, Least

from example_project.app.models import Person, Task
from tests.factories import PersonFactory, TaskFactory
from tests.helpers import exact, parametrize_helper
from undine.errors.exceptions import PaginationArgumentValidationError
from undine.relay import PaginationHandler, offset_to_cursor
from undine.typing import ToManyField
from undine.utils.model_utils import SubqueryCount


class PaginationParams(NamedTuple):
    first: str | int | None = None
    last: str | int | None = None
    offset: str | int | None = None
    after: str | None = None
    before: str | None = None
    max_limit: str | int | None = 100
    typename: str = "Test"


class InputParams(NamedTuple):
    params: PaginationParams
    start: int | Expression | None = None
    stop: int | Expression | None = None
    total_count: int | None = 200


class ErrorParams(NamedTuple):
    params: PaginationParams
    errors: str | None = None


@pytest.mark.parametrize(
    **parametrize_helper(
        {
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
            ),
            "offset": InputParams(
                params=PaginationParams(offset=1),
                start=1,
                stop=101,
            ),
            "max limit": InputParams(
                params=PaginationParams(max_limit=1),
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
                start=200,
                stop=200,
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
                start=200,
                stop=200,
            ),
        },
    ),
)
@pytest.mark.django_db
def test_pagination_handler__paginate_queryset(params, start, stop, total_count, undine_settings):
    pagination = PaginationHandler(**params._asdict())

    pagination.total_count = total_count

    queryset = pagination.paginate_queryset(Task.objects.all())

    assert queryset._hints[undine_settings.CONNECTION_TOTAL_COUNT_KEY] == total_count
    assert queryset._hints[undine_settings.CONNECTION_START_INDEX_KEY] == start
    assert queryset._hints[undine_settings.CONNECTION_STOP_INDEX_KEY] == stop


@pytest.mark.parametrize(
    **parametrize_helper(
        {
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
                params=PaginationParams(first=2, max_limit=1),
                errors="Requesting first 2 records exceeds the limit of 1.",
            ),
            "last exceeds max limit": ErrorParams(
                params=PaginationParams(last=2, max_limit=1),
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
                params=PaginationParams(max_limit="foo"),
                errors="`max_limit` must be `None` or a positive integer, got: 'foo'",
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
        },
    ),
)
def test_pagination_handler__validation_errors(params, errors, undine_settings):
    with pytest.raises(PaginationArgumentValidationError, match=exact(errors)):
        PaginationHandler(**params._asdict())


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__requires_total_count(undine_settings):
    TaskFactory.create_batch(3)

    pagination = PaginationHandler(typename="A", max_limit=100)
    pagination.requires_total_count = True
    queryset = pagination.paginate_queryset(Task.objects.all())

    assert queryset._hints[undine_settings.CONNECTION_TOTAL_COUNT_KEY] == 3
    assert queryset._hints[undine_settings.CONNECTION_START_INDEX_KEY] == 0
    assert queryset._hints[undine_settings.CONNECTION_STOP_INDEX_KEY] == 3


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__no_max_limit(undine_settings):
    TaskFactory.create_batch(3)

    pagination = PaginationHandler(typename="A", max_limit=None)
    queryset = pagination.paginate_queryset(Task.objects.all())

    assert queryset._hints[undine_settings.CONNECTION_TOTAL_COUNT_KEY] is None
    assert queryset._hints[undine_settings.CONNECTION_START_INDEX_KEY] == 0
    assert queryset._hints[undine_settings.CONNECTION_STOP_INDEX_KEY] is None


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__no_max_limit__requires_total_count(undine_settings):
    TaskFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", max_limit=None)
    pagination.requires_total_count = True
    queryset = pagination.paginate_queryset(Task.objects.all())

    assert queryset._hints[undine_settings.CONNECTION_TOTAL_COUNT_KEY] == 3
    assert queryset._hints[undine_settings.CONNECTION_START_INDEX_KEY] == 0
    assert queryset._hints[undine_settings.CONNECTION_STOP_INDEX_KEY] == 3


@pytest.mark.django_db
def test_pagination_handler__paginate_queryset__no_max_limit__filter_last(undine_settings):
    TaskFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", last=2, max_limit=None)
    queryset = pagination.paginate_queryset(Task.objects.all())

    assert queryset._hints[undine_settings.CONNECTION_TOTAL_COUNT_KEY] == 3
    assert queryset._hints[undine_settings.CONNECTION_START_INDEX_KEY] == 1
    assert queryset._hints[undine_settings.CONNECTION_STOP_INDEX_KEY] == 3


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "none": InputParams(
                params=PaginationParams(),
                start=Value(0),
                stop=Value(0) + Value(100),
            ),
            "after": InputParams(
                params=PaginationParams(after=offset_to_cursor("Test", 0)),
                start=Value(1),
                stop=Value(1) + Value(100),
            ),
            "before": InputParams(
                params=PaginationParams(before=offset_to_cursor("Test", 10)),
                start=Value(0),
                stop=Least(Value(0) + Value(100), Value(10)),
            ),
            "first": InputParams(
                params=PaginationParams(first=1),
                start=Value(0),
                stop=Value(0) + Value(1),
            ),
            # "last": Separate test below.
            "offset": InputParams(
                params=PaginationParams(offset=1),
                start=Value(1),
                stop=Value(1) + Value(100),
            ),
            "max limit": InputParams(
                params=PaginationParams(max_limit=1),
                start=Value(0),
                stop=Value(0) + Value(1),
            ),
            "after and before": InputParams(
                params=PaginationParams(after=offset_to_cursor("Test", 1), before=offset_to_cursor("Test", 99)),
                start=Value(2),
                stop=Least(Value(2) + Value(100), Value(99)),
            ),
            "first and last": InputParams(
                params=PaginationParams(first=10, last=8),
                start=Greatest(Value(0) + Value(10) - Value(8), Value(0)),
                stop=Value(0) + Value(10),
            ),
            "before and first": InputParams(
                params=PaginationParams(before=offset_to_cursor("Test", 50), first=10),
                start=Value(0),
                stop=Least(Value(0) + Value(10), Value(50)),
            ),
            "before and last": InputParams(
                params=PaginationParams(before=offset_to_cursor("Test", 50), last=10),
                start=Greatest(Value(50) - Value(10), Value(0)),
                stop=Value(50),
            ),
            "after and first": InputParams(
                params=PaginationParams(after=offset_to_cursor("Test", 50), first=10),
                start=Value(51),
                stop=Value(51) + Value(10),
            ),
            # "after and last": Separate test below.
            "after and before and first": InputParams(
                params=PaginationParams(
                    after=offset_to_cursor("Test", 1),
                    before=offset_to_cursor("Test", 99),
                    first=10,
                ),
                start=Value(2),
                stop=Least(Value(2) + Value(10), Value(99)),
            ),
            "after and before and last": InputParams(
                params=PaginationParams(
                    after=offset_to_cursor("Test", 1),
                    before=offset_to_cursor("Test", 99),
                    last=10,
                ),
                start=Greatest(Value(99) - Value(10), Value(2)),
                stop=Value(99),
            ),
            "after and before and first and last": InputParams(
                params=PaginationParams(
                    after=offset_to_cursor("Test", 1),
                    before=offset_to_cursor("Test", 99),
                    first=10,
                    last=8,
                ),
                start=Greatest(Least(Value(2) + Value(10), Value(99)) - Value(8), Value(2)),
                stop=Least(Value(2) + Value(10), Value(99)),
            ),
            "after bigger than total count": InputParams(
                params=PaginationParams(after=offset_to_cursor("Test", 201)),
                start=Value(202),
                stop=Value(202) + Value(100),
            ),
            "before bigger than total count": InputParams(
                params=PaginationParams(before=offset_to_cursor("Test", 201)),
                start=Value(0),
                stop=Least(Value(0) + Value(100), Value(201)),
            ),
            "first bigger than interval from after to before": InputParams(
                params=PaginationParams(
                    after=offset_to_cursor("Test", 9),
                    before=offset_to_cursor("Test", 20),
                    first=20,
                ),
                start=Value(10),
                stop=Least(Value(10) + Value(20), Value(20)),
            ),
            "last bigger than interval from after to before": InputParams(
                params=PaginationParams(
                    after=offset_to_cursor("Test", 9),
                    before=offset_to_cursor("Test", 20),
                    last=20,
                ),
                start=Greatest(Value(20) - Value(20), Value(10)),
                stop=Value(20),
            ),
            "offset zero": InputParams(
                params=PaginationParams(offset=0),
                start=Value(0),
                stop=Value(0) + Value(100),
            ),
            "offset bigger than total count": InputParams(
                params=PaginationParams(offset=201),
                start=Value(201),
                stop=Value(201) + Value(100),
            ),
        },
    ),
)
def test_pagination_handler__paginate_prefetch_queryset(params, start, stop, total_count, undine_settings):
    related_field: ToManyField = Task._meta.get_field("assignees")  # type: ignore[attr-defined]

    pagination = PaginationHandler(**params._asdict())
    queryset = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field)

    assert undine_settings.CONNECTION_TOTAL_COUNT_KEY not in queryset.query.annotations
    assert queryset.query.annotations[undine_settings.CONNECTION_START_INDEX_KEY] == start
    assert queryset.query.annotations[undine_settings.CONNECTION_STOP_INDEX_KEY] == stop


def test_pagination_handler__paginate_prefetch_queryset__last(undine_settings):
    related_field: ToManyField = Task._meta.get_field("assignees")  # type: ignore[attr-defined]

    pagination = PaginationHandler(typename="Test", last=2, max_limit=100)
    queryset = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field)

    assert undine_settings.CONNECTION_TOTAL_COUNT_KEY in queryset.query.annotations
    total_count = queryset.query.annotations[undine_settings.CONNECTION_TOTAL_COUNT_KEY]
    assert isinstance(total_count, SubqueryCount)

    # Greatest(total_count - Value(2), Value(0))
    start = queryset.query.annotations[undine_settings.CONNECTION_START_INDEX_KEY]
    assert isinstance(start, Greatest)
    expressions = start.get_source_expressions()
    assert len(expressions) == 2, expressions
    assert isinstance(expressions[0], CombinedExpression)
    assert isinstance(expressions[0].lhs, SubqueryCount)
    assert expressions[0].rhs == Value(2)
    assert expressions[1] == Value(0)

    stop = queryset.query.annotations[undine_settings.CONNECTION_STOP_INDEX_KEY]
    assert isinstance(stop, SubqueryCount)


def test_pagination_handler__paginate_prefetch_queryset__after_and_last(undine_settings):
    related_field: ToManyField = Task._meta.get_field("assignees")  # type: ignore[attr-defined]

    pagination = PaginationHandler(typename="Test", after=offset_to_cursor("Test", 50), last=10, max_limit=100)
    queryset = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field)

    assert undine_settings.CONNECTION_TOTAL_COUNT_KEY in queryset.query.annotations
    total_count = queryset.query.annotations[undine_settings.CONNECTION_TOTAL_COUNT_KEY]
    assert isinstance(total_count, SubqueryCount)

    # Greatest(total_count - Value(10), Value(51))
    start = queryset.query.annotations[undine_settings.CONNECTION_START_INDEX_KEY]
    assert isinstance(start, Greatest)
    expressions = start.get_source_expressions()
    assert len(expressions) == 2, expressions
    assert isinstance(expressions[0], CombinedExpression)
    assert isinstance(expressions[0].lhs, SubqueryCount)
    assert expressions[0].rhs == Value(10)
    assert expressions[1] == Value(51)

    stop = queryset.query.annotations[undine_settings.CONNECTION_STOP_INDEX_KEY]
    assert isinstance(stop, SubqueryCount)


def test_pagination_handler__paginate_prefetch_queryset__requires_total_count(undine_settings):
    related_field: ToManyField = Task._meta.get_field("assignees")  # type: ignore[attr-defined]

    pagination = PaginationHandler(typename="Test", max_limit=100)
    pagination.requires_total_count = True
    queryset = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field)

    assert undine_settings.CONNECTION_TOTAL_COUNT_KEY in queryset.query.annotations
    total_count = queryset.query.annotations[undine_settings.CONNECTION_TOTAL_COUNT_KEY]
    assert isinstance(total_count, SubqueryCount)

    assert queryset.query.annotations[undine_settings.CONNECTION_START_INDEX_KEY] == Value(0)
    assert queryset.query.annotations[undine_settings.CONNECTION_STOP_INDEX_KEY] == Value(0) + Value(100)


@pytest.mark.django_db
def test_pagination_handler__paginate_prefetch_queryset__no_max_limit(undine_settings):
    related_field: ToManyField = Task._meta.get_field("assignees")  # type: ignore[attr-defined]

    PersonFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", max_limit=None)
    queryset = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field)

    assert undine_settings.CONNECTION_TOTAL_COUNT_KEY not in queryset.query.annotations

    assert queryset.query.annotations[undine_settings.CONNECTION_START_INDEX_KEY] == Value(0)

    assert undine_settings.CONNECTION_STOP_INDEX_KEY not in queryset.query.annotations


@pytest.mark.django_db
def test_pagination_handler__paginate_prefetch_queryset__no_max_limit__requires_total_count(undine_settings):
    related_field: ToManyField = Task._meta.get_field("assignees")  # type: ignore[attr-defined]

    PersonFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", max_limit=None)
    pagination.requires_total_count = True
    queryset = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field)

    assert undine_settings.CONNECTION_TOTAL_COUNT_KEY in queryset.query.annotations
    total_count = queryset.query.annotations[undine_settings.CONNECTION_TOTAL_COUNT_KEY]
    assert isinstance(total_count, SubqueryCount)

    assert queryset.query.annotations[undine_settings.CONNECTION_START_INDEX_KEY] == Value(0)

    assert undine_settings.CONNECTION_STOP_INDEX_KEY not in queryset.query.annotations


@pytest.mark.django_db
def test_pagination_handler__paginate_prefetch_queryset__no_max_limit__last(undine_settings):
    related_field: ToManyField = Task._meta.get_field("assignees")  # type: ignore[attr-defined]

    PersonFactory.create_batch(3)

    pagination = PaginationHandler(typename="Test", last=2, max_limit=None)
    queryset = pagination.paginate_prefetch_queryset(Person.objects.all(), related_field)

    assert undine_settings.CONNECTION_TOTAL_COUNT_KEY in queryset.query.annotations
    total_count = queryset.query.annotations[undine_settings.CONNECTION_TOTAL_COUNT_KEY]
    assert isinstance(total_count, SubqueryCount)

    # Greatest(total_count - Value(2), Value(0))
    start = queryset.query.annotations[undine_settings.CONNECTION_START_INDEX_KEY]
    assert isinstance(start, Greatest)
    expressions = start.get_source_expressions()
    assert len(expressions) == 2, expressions
    assert isinstance(expressions[0], CombinedExpression)
    assert isinstance(expressions[0].lhs, SubqueryCount)
    assert expressions[0].rhs == Value(2)
    assert expressions[1] == Value(0)

    stop = queryset.query.annotations[undine_settings.CONNECTION_STOP_INDEX_KEY]
    assert isinstance(stop, SubqueryCount)
