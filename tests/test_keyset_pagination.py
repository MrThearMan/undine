from __future__ import annotations

import json

import pytest
from django.db.models.functions import Length

from example_project.app.models import Person, Task, TaskStep
from tests.factories import PersonFactory, TaskFactory, TaskStepFactory
from tests.helpers import keyset_cursor
from undine import Entrypoint, Field, Order, OrderSet, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPaginationArgumentValidationError
from undine.relay import Connection, CursorPaginationHandler, decode_base64, encode_base64


def create_task_schema(*, page_size: int | None = 100):
    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()
        points = Order()
        points_nulls_first = Order("points", null_placement="first")
        points_nulls_last = Order("points", null_placement="last")

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType, page_size=page_size))

    return create_schema(query=Query)


PAGE_QUERY = """
    query Tasks($first: Int, $after: String, $orderBy: [TaskOrderSet!]) {
      tasks(first: $first, after: $after, orderBy: $orderBy) {
        pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
        edges { cursor node { name points } }
      }
    }
"""


def paginate_all(graphql, *, page_size: int, order_by: list[str] | None = None) -> list[str]:
    """Page through the whole connection, returning the name of every node that was delivered."""
    names: list[str] = []
    cursor: str | None = None

    tries = 100
    while tries > 0:
        tries -= 1
        variables: dict = {"first": page_size, "after": cursor}
        if order_by is not None:
            variables["orderBy"] = order_by

        response = graphql(PAGE_QUERY, variables=variables)
        assert response.has_errors is False, response.errors

        connection = response.data["tasks"]
        names += [edge["node"]["name"] for edge in connection["edges"]]

        if not connection["pageInfo"]["hasNextPage"]:
            return names

        cursor = connection["pageInfo"]["endCursor"]

    msg = "Pagination did not return all results"
    raise AssertionError(msg)


def cursor_to_values(typename: str, cursor: str) -> dict[str, str | None]:
    decoded = decode_base64(cursor)
    prefix = f"connection:{typename}:"

    if not decoded.startswith(prefix):
        msg = f"Not a valid cursor for type '{typename}'."
        raise GraphQLPaginationArgumentValidationError(msg)

    payload = decoded.removeprefix(prefix)

    string_values = json.loads(payload)
    is_valid = isinstance(string_values, dict) and all(
        isinstance(key, str) and (value is None or isinstance(value, str)) for key, value in string_values.items()
    )
    if not is_valid:
        msg = f"Not a valid cursor for type '{typename}'."
        raise GraphQLPaginationArgumentValidationError(msg)

    return string_values


def values_to_cursor(typename: str, values: dict[str, str | None]) -> str:
    payload = json.dumps(values, separators=(",", ":"))
    return encode_base64(f"connection:{typename}:{payload}")


# Stability


@pytest.mark.django_db
def test_pagination__cursor__insert_before_cursor_does_not_duplicate(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    for name in ["b", "c", "d", "e"]:
        TaskFactory.create(name=name)

    response = graphql(PAGE_QUERY, variables={"first": 2, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["b", "c"]

    cursor = response.data["tasks"]["pageInfo"]["endCursor"]

    TaskFactory.create(name="a")

    response = graphql(PAGE_QUERY, variables={"first": 2, "after": cursor, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["d", "e"]


@pytest.mark.django_db
def test_pagination__cursor__delete_before_cursor_does_not_skip(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    for name in ["b", "c", "d", "e"]:
        TaskFactory.create(name=name)

    response = graphql(PAGE_QUERY, variables={"first": 2, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["b", "c"]

    cursor = response.data["tasks"]["pageInfo"]["endCursor"]

    Task.objects.filter(name="b").delete()

    response = graphql(PAGE_QUERY, variables={"first": 2, "after": cursor, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["d", "e"]


# Ordering


@pytest.mark.django_db
def test_pagination__cursor__ties_are_neither_skipped_nor_repeated(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    for _ in range(5):
        TaskFactory.create(name="same")

    names = paginate_all(graphql, page_size=2, order_by=["nameAsc"])
    assert names == ["same"] * 5


@pytest.mark.django_db
def test_pagination__cursor__descending(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    for name in ["a", "b", "c", "d", "e"]:
        TaskFactory.create(name=name)

    names = paginate_all(graphql, page_size=2, order_by=["nameDesc"])
    assert names == ["e", "d", "c", "b", "a"]


@pytest.mark.django_db
def test_pagination__cursor__nulls_first(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a", points=1)
    TaskFactory.create(name="b", points=None)
    TaskFactory.create(name="c", points=2)
    TaskFactory.create(name="d", points=None)
    TaskFactory.create(name="e", points=3)

    names = paginate_all(graphql, page_size=2, order_by=["pointsNullsFirstAsc"])
    assert names == ["b", "d", "a", "c", "e"]


@pytest.mark.django_db
def test_pagination__cursor__nulls_last(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a", points=1)
    TaskFactory.create(name="b", points=None)
    TaskFactory.create(name="c", points=2)
    TaskFactory.create(name="d", points=None)
    TaskFactory.create(name="e", points=3)

    names = paginate_all(graphql, page_size=2, order_by=["pointsNullsLastAsc"])
    assert names == ["a", "c", "e", "b", "d"]


@pytest.mark.django_db
def test_pagination__cursor__nulls_last__descending(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a", points=1)
    TaskFactory.create(name="b", points=None)
    TaskFactory.create(name="c", points=2)
    TaskFactory.create(name="d", points=None)
    TaskFactory.create(name="e", points=3)

    names = paginate_all(graphql, page_size=2, order_by=["pointsNullsLastDesc"])
    assert names == ["e", "c", "a", "b", "d"]


@pytest.mark.django_db
def test_pagination__cursor__nulls_default_placement(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a", points=1)
    TaskFactory.create(name="b", points=None)
    TaskFactory.create(name="c", points=2)
    TaskFactory.create(name="d", points=None)
    TaskFactory.create(name="e", points=3)

    response = graphql(PAGE_QUERY, variables={"orderBy": ["pointsAsc"]})
    assert response.has_errors is False, response.errors
    expected = [edge["node"]["name"] for edge in response.data["tasks"]["edges"]]

    names = paginate_all(graphql, page_size=2, order_by=["pointsAsc"])
    assert names == expected


@pytest.mark.django_db
def test_pagination__cursor__no_ordering_defaults_to_primary_key(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    for name in ["c", "a", "b", "e", "d"]:
        TaskFactory.create(name=name)

    names = paginate_all(graphql, page_size=2)
    assert names == ["c", "a", "b", "e", "d"]


# Backwards pagination


@pytest.mark.django_db
def test_pagination__cursor__last_returns_same_order_as_first(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    for name in ["a", "b", "c", "d", "e"]:
        TaskFactory.create(name=name)

    query = """
        query Tasks($last: Int, $before: String) {
          tasks(last: $last, before: $before, orderBy: [nameAsc]) {
            pageInfo { hasNextPage hasPreviousPage startCursor }
            edges { node { name } }
          }
        }
    """

    response = graphql(query, variables={"last": 2})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["d", "e"]
    assert response.data["tasks"]["pageInfo"]["hasPreviousPage"] is True
    assert response.data["tasks"]["pageInfo"]["hasNextPage"] is False

    cursor = response.data["tasks"]["pageInfo"]["startCursor"]

    response = graphql(query, variables={"last": 2, "before": cursor})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["b", "c"]
    assert response.data["tasks"]["pageInfo"]["hasNextPage"] is True
    assert response.data["tasks"]["pageInfo"]["hasPreviousPage"] is True

    cursor = response.data["tasks"]["pageInfo"]["startCursor"]

    response = graphql(query, variables={"last": 2, "before": cursor})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["a"]
    assert response.data["tasks"]["pageInfo"]["hasPreviousPage"] is False


# Page info


@pytest.mark.django_db
def test_pagination__cursor__page_info__empty_result(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    response = graphql(PAGE_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors
    assert response.data["tasks"]["pageInfo"] == {
        "hasNextPage": False,
        "hasPreviousPage": False,
        "startCursor": None,
        "endCursor": None,
    }


@pytest.mark.django_db
def test_pagination__cursor__page_info__single_page(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a")
    TaskFactory.create(name="b")

    response = graphql(PAGE_QUERY, variables={"first": 2, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert response.data["tasks"]["pageInfo"]["hasNextPage"] is False
    assert response.data["tasks"]["pageInfo"]["hasPreviousPage"] is False


@pytest.mark.django_db
def test_pagination__cursor__page_info__both_ends(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    for name in ["a", "b", "c"]:
        TaskFactory.create(name=name)

    response = graphql(PAGE_QUERY, variables={"first": 1, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert response.data["tasks"]["pageInfo"]["hasNextPage"] is True
    assert response.data["tasks"]["pageInfo"]["hasPreviousPage"] is False

    cursor = response.data["tasks"]["pageInfo"]["endCursor"]

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": cursor, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert response.data["tasks"]["pageInfo"]["hasNextPage"] is True
    assert response.data["tasks"]["pageInfo"]["hasPreviousPage"] is True

    cursor = response.data["tasks"]["pageInfo"]["endCursor"]

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": cursor, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["c"]
    assert response.data["tasks"]["pageInfo"]["hasNextPage"] is False
    assert response.data["tasks"]["pageInfo"]["hasPreviousPage"] is True


# Invalid cursors


@pytest.mark.django_db
def test_pagination__cursor__replayed_under_different_ordering(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    for name in ["a", "b", "c"]:
        TaskFactory.create(name=name)

    response = graphql(PAGE_QUERY, variables={"first": 1, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors

    cursor = response.data["tasks"]["pageInfo"]["endCursor"]

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": cursor, "orderBy": ["nameAsc", "pointsAsc"]})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "different ordering" in response.errors[0]["message"]


@pytest.mark.django_db
def test_pagination__cursor__replayed_under_different_ordering__same_field_count(graphql, undine_settings) -> None:
    """
    A cursor built under one ordering must be rejected under another ordering with the same number
    of fields, not just a different number of fields: the cursor is keyed by field name, not position,
    so a 'pointsAsc' cursor cannot be silently reinterpreted as a 'nameAsc' cursor.
    """
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a", points=1)
    TaskFactory.create(name="b", points=2)

    response = graphql(PAGE_QUERY, variables={"first": 1, "orderBy": ["pointsAsc"]})
    assert response.has_errors is False, response.errors

    cursor = response.data["tasks"]["pageInfo"]["endCursor"]

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": cursor, "orderBy": ["nameAsc"]})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "different ordering" in response.errors[0]["message"]


@pytest.mark.django_db
def test_pagination__cursor__replayed_under_different_ordering__pk_vs_points(graphql, undine_settings) -> None:
    """
    A cursor built while paginating by the default primary-key ordering must be rejected when
    replayed against a 'points'-ordered query, even though both use an integer field: the cursor
    is keyed by field name ('pk' vs. 'points'), not by value type or position.
    """
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a", points=1)
    TaskFactory.create(name="b", points=2)

    response = graphql(PAGE_QUERY, variables={"first": 1})
    assert response.has_errors is False, response.errors

    cursor = response.data["tasks"]["pageInfo"]["endCursor"]
    assert cursor_to_values("TaskType", cursor) == {"pk": "1"}

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": cursor, "orderBy": ["pointsAsc"]})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "different ordering" in response.errors[0]["message"]


@pytest.mark.django_db
def test_pagination__cursor__malformed_cursor(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a")

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": "not-a-cursor"})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"


@pytest.mark.django_db
def test_pagination__cursor__built_for_another_type(graphql, undine_settings) -> None:
    """A cursor naming a different type is rejected, so it cannot be replayed against this connection."""
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a")

    cursor = values_to_cursor("PersonType", {"pk": "1"})

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": cursor})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert response.errors[0]["message"] == "Argument 'after' is invalid: Not a valid cursor for type 'TaskType'."


@pytest.mark.django_db
def test_pagination__cursor__payload_is_not_an_object(graphql, undine_settings) -> None:
    """A cursor whose payload is not a mapping of ordering values is rejected."""
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a")

    cursor = encode_base64('connection:TaskType:["1"]')

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": cursor})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert response.errors[0]["message"] == "Argument 'after' is invalid: Not a valid cursor for type 'TaskType'."


@pytest.mark.django_db
def test_pagination__cursor__value_of_wrong_type(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="a")

    cursor = values_to_cursor("TaskType", {"pk": "not-an-integer"})

    response = graphql(PAGE_QUERY, variables={"first": 1, "after": cursor})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"


# Nested connections


def create_nested_schema():
    class PersonOrderSet(OrderSet[Person], auto=False):
        name = Order()

    class PersonType(QueryType[Person], auto=False, orderset=PersonOrderSet):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    return create_schema(query=Query)


NESTED_QUERY = """
    query Assignees($first: Int, $after: String) {
      tasks {
        edges {
          node {
            name
            assignees(first: $first, after: $after, orderBy: [nameAsc]) {
              totalCount
              pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
              edges { node { name } }
            }
          }
        }
      }
    }
"""


@pytest.mark.django_db
def test_pagination__cursor__nested(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_nested_schema()

    people = [PersonFactory.create(name=name) for name in ["a", "b", "c", "d"]]
    TaskFactory.create(name="Task 1", assignees=people)
    TaskFactory.create(name="Task 2", assignees=people[:2])

    response = graphql(NESTED_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    first_task = response.data["tasks"]["edges"][0]["node"]["assignees"]
    assert [edge["node"]["name"] for edge in first_task["edges"]] == ["a", "b"]
    assert first_task["totalCount"] == 4
    assert first_task["pageInfo"]["hasNextPage"] is True

    second_task = response.data["tasks"]["edges"][1]["node"]["assignees"]
    assert [edge["node"]["name"] for edge in second_task["edges"]] == ["a", "b"]
    assert second_task["totalCount"] == 2
    assert second_task["pageInfo"]["hasNextPage"] is False

    cursor = first_task["pageInfo"]["endCursor"]

    response = graphql(NESTED_QUERY, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    first_task = response.data["tasks"]["edges"][0]["node"]["assignees"]
    assert [edge["node"]["name"] for edge in first_task["edges"]] == ["c", "d"]
    assert first_task["pageInfo"]["hasNextPage"] is False
    assert first_task["pageInfo"]["hasPreviousPage"] is True

    # The total count must stay the true partition total, not the number of rows after the cursor.
    assert first_task["totalCount"] == 4

    second_task = response.data["tasks"]["edges"][1]["node"]["assignees"]
    assert second_task["edges"] == []
    # Total count is annotated to the rows, so it cannot be known for an empty partition page.
    assert second_task["totalCount"] == 0


@pytest.mark.django_db
def test_pagination__cursor__nested__last(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_nested_schema()

    people = [PersonFactory.create(name=name) for name in ["a", "b", "c", "d"]]
    TaskFactory.create(name="Task 1", assignees=people)

    query = """
        query {
          tasks {
            edges {
              node {
                assignees(last: 2, orderBy: [nameAsc]) {
                  totalCount
                  pageInfo { hasNextPage hasPreviousPage }
                  edges { node { name } }
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assignees = response.data["tasks"]["edges"][0]["node"]["assignees"]
    assert [edge["node"]["name"] for edge in assignees["edges"]] == ["c", "d"]
    assert assignees["pageInfo"]["hasPreviousPage"] is True
    assert assignees["totalCount"] == 4


# Ordering by expressions and related fields


@pytest.mark.django_db
def test_pagination__cursor__order_by_expression(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        name_length = Order(Length("name"))

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    for name in ["aaaa", "bb", "ccc", "d", "eeeee"]:
        TaskFactory.create(name=name)

    names = paginate_all(graphql, page_size=2, order_by=["nameLengthAsc"])
    assert names == ["d", "bb", "ccc", "aaaa", "eeeee"]


@pytest.mark.django_db
def test_pagination__cursor__order_by_related_field(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        project_name = Order("project__name")

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    for name in ["a", "b", "c", "d"]:
        TaskFactory.create(name=name, project__name=f"Project {name}")

    names = paginate_all(graphql, page_size=2, order_by=["projectNameAsc"])
    assert names == ["a", "b", "c", "d"]


@pytest.mark.django_db
def test_pagination__cursor__order_by_field_that_was_not_selected(graphql, undine_settings) -> None:
    """The query optimizer defers fields that were not selected, but ordering values must still be available."""

    class TaskOrderSet(OrderSet[Task], auto=False):
        points = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="a", points=3)
    TaskFactory.create(name="b", points=1)
    TaskFactory.create(name="c", points=2)

    query = """
        query Tasks($first: Int, $after: String) {
          tasks(first: $first, after: $after, orderBy: [pointsAsc]) {
            pageInfo { hasNextPage endCursor }
            edges { node { name } }
          }
        }
    """

    names: list[str] = []
    cursor: str | None = None

    while True:
        response = graphql(query, variables={"first": 1, "after": cursor})
        assert response.has_errors is False, response.errors

        connection = response.data["tasks"]
        names += [edge["node"]["name"] for edge in connection["edges"]]

        if not connection["pageInfo"]["hasNextPage"]:
            break

        cursor = connection["pageInfo"]["endCursor"]

    assert names == ["b", "c", "a"]


# Custom pagination handler


@pytest.mark.django_db
def test_pagination__cursor__index_based_pagination_handler(graphql, undine_settings) -> None:
    """A `Connection` can still be paginated with index based cursors by overriding the handler."""

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(Connection(PersonType, page_size=2))

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    people = [PersonFactory.create(name=name) for name in ["a", "b", "c"]]
    TaskFactory.create(name="Task 1", assignees=people)

    query = """
        query {
          tasks {
            edges {
              node {
                assignees {
                  totalCount
                  pageInfo { hasNextPage hasPreviousPage startCursor }
                  edges { cursor node { name } }
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assignees = response.data["tasks"]["edges"][0]["node"]["assignees"]
    assert [edge["node"]["name"] for edge in assignees["edges"]] == ["a", "b"]
    assert assignees["totalCount"] == 3
    assert assignees["pageInfo"]["hasNextPage"] is True
    assert assignees["pageInfo"]["hasPreviousPage"] is False
    assert assignees["pageInfo"]["startCursor"] == keyset_cursor("PersonType", 1)


@pytest.mark.django_db
def test_pagination__cursor__primary_key_field_in_ordering(graphql, undine_settings) -> None:
    """Ordering by the primary key's own field name must not append a second pk ordering."""

    class TaskOrderSet(OrderSet[Task], auto=False):
        id = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    tasks = [TaskFactory.create(name=name) for name in ["a", "b", "c"]]

    query = """
        query {
          tasks(first: 2, orderBy: [idAsc]) {
            edges { cursor node { name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert [edge["node"]["name"] for edge in response.data["tasks"]["edges"]] == ["a", "b"]

    # The cursor holds only the primary key, since the ordering already contains it.
    cursors = [edge["cursor"] for edge in response.data["tasks"]["edges"]]
    assert [cursor_to_values("TaskType", cursor) for cursor in cursors] == [
        {"id": str(tasks[0].pk)},
        {"id": str(tasks[1].pk)},
    ]


# Argument validation


def test_pagination__cursor__invalid_page_size() -> None:
    with pytest.raises(GraphQLPaginationArgumentValidationError):
        CursorPaginationHandler(typename="TaskType", page_size=0)


@pytest.mark.django_db
def test_pagination__cursor__primary_key_already_in_ordering(graphql, undine_settings) -> None:
    """Ordering by an `Order()` named "pk" must not append a second pk ordering either."""

    class TaskOrderSet(OrderSet[Task], auto=False):
        pk = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    for name in ["a", "b", "c"]:
        TaskFactory.create(name=name)

    names = paginate_all(graphql, page_size=2, order_by=["pkDesc"])
    assert names == ["c", "b", "a"]

    query = """
        query {
          tasks(first: 2, orderBy: [pkDesc]) {
            edges { cursor node { name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # The cursor holds only one ordering value, since the ordering already contains the pk.
    cursors = [edge["cursor"] for edge in response.data["tasks"]["edges"]]
    assert [len(cursor_to_values("TaskType", cursor)) for cursor in cursors] == [1, 1]


@pytest.mark.django_db
def test_pagination__cursor__index_based_pagination_handler__reverse_foreign_key(graphql, undine_settings) -> None:
    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType, page_size=2))

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    for name in ["a", "b", "c"]:
        TaskStepFactory.create(name=name, task=task)

    TaskFactory.create(name="Task 2")

    query = """
        query {
          tasks {
            edges {
              node {
                name
                steps {
                  totalCount
                  pageInfo { hasNextPage hasPreviousPage }
                  edges { node { name } }
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    steps = response.data["tasks"]["edges"][0]["node"]["steps"]
    assert [edge["node"]["name"] for edge in steps["edges"]] == ["a", "b"]
    assert steps["totalCount"] == 3
    assert steps["pageInfo"]["hasNextPage"] is True

    # No rows, so the pagination annotations cannot be read.
    empty_steps = response.data["tasks"]["edges"][1]["node"]["steps"]
    assert empty_steps["edges"] == []
    assert empty_steps["totalCount"] == 0
    assert empty_steps["pageInfo"]["hasNextPage"] is False


# Argument validation


ARGUMENT_QUERY = """
    query Tasks($first: Int, $last: Int, $after: String, $before: String) {
      tasks(first: $first, last: $last, after: $after, before: $before) {
        edges { node { name } }
      }
    }
"""


@pytest.mark.django_db
def test_pagination__cursor__arguments__after_and_before(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    cursor = values_to_cursor("TaskType", {"pk": "1"})

    response = graphql(ARGUMENT_QUERY, variables={"after": cursor, "before": cursor})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "Cannot use both 'after' and 'before' arguments together." in response.error_message(0)


@pytest.mark.django_db
def test_pagination__cursor__arguments__first_not_positive(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    response = graphql(ARGUMENT_QUERY, variables={"first": 0})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "Argument 'first' must be a positive integer." in response.error_message(0)


@pytest.mark.django_db
def test_pagination__cursor__arguments__first_exceeds_page_size(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema(page_size=2)

    response = graphql(ARGUMENT_QUERY, variables={"first": 5})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "Requesting first 5 records exceeds the maximum page size of 2." in response.error_message(0)


@pytest.mark.django_db
def test_pagination__cursor__arguments__first_and_last(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    response = graphql(ARGUMENT_QUERY, variables={"first": 1, "last": 1})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "Cannot use both 'first' and 'last' arguments together." in response.error_message(0)


@pytest.mark.django_db
def test_pagination__cursor__arguments__first_and_before(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    cursor = values_to_cursor("TaskType", {"pk": "1"})

    response = graphql(ARGUMENT_QUERY, variables={"first": 1, "before": cursor})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "Cannot use both 'first' and 'before' arguments together." in response.error_message(0)


@pytest.mark.django_db
def test_pagination__cursor__arguments__last_not_positive(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    response = graphql(ARGUMENT_QUERY, variables={"last": 0})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "Argument 'last' must be a positive integer." in response.error_message(0)


@pytest.mark.django_db
def test_pagination__cursor__arguments__last_exceeds_page_size(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema(page_size=2)

    response = graphql(ARGUMENT_QUERY, variables={"last": 5})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "Requesting last 5 records exceeds the maximum page size of 2." in response.error_message(0)


@pytest.mark.django_db
def test_pagination__cursor__arguments__last_and_after(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_task_schema()

    cursor = values_to_cursor("TaskType", {"pk": "1"})

    response = graphql(ARGUMENT_QUERY, variables={"last": 1, "after": cursor})
    assert response.has_errors is True
    assert response.errors[0]["extensions"]["error_code"] == "INVALID_PAGINATION_ARGUMENTS"
    assert "Cannot use both 'last' and 'after' arguments together." in response.error_message(0)
