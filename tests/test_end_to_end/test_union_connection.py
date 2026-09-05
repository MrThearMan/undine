from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.db.models.functions import Lower, Reverse, Substr

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import keyset_cursor, walk_connection_forward_and_backward
from undine import (
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    Order,
    OrderSet,
    QueryType,
    RootType,
    UnionType,
    create_schema,
)
from undine.exceptions import EmptyFilterResult, GraphQLPermissionError
from undine.relay import Connection
from undine.typing import DjangoExpression

CONNECTION_QUERY = """
    query Searchables($first: Int, $last: Int, $after: String, $before: String) {
      searchables(first: $first, last: $last, after: $after, before: $before) {
        totalCount
        pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
        edges {
          cursor
          node {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
      }
    }
"""

NODES_QUERY = """
    query {
      searchables {
        edges {
          node {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
      }
    }
"""


def create_union_schema():
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

    return create_schema(query=Query)


# Paging


@pytest.mark.django_db
def test_union_connection__empty(graphql, undine_settings) -> None:
    """With no rows in either member model, the connection has no edges and no cursors."""
    undine_settings.SCHEMA = create_union_schema()

    response = graphql(CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 0,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": None,
                "endCursor": None,
            },
            "edges": [],
        },
    }


@pytest.mark.django_db
def test_union_connection__first(graphql, undine_settings) -> None:
    """A page taken with 'first' spans both members of the union, and 'totalCount' counts rows in both."""
    undine_settings.SCHEMA = create_union_schema()

    task_1 = TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    project_1 = ProjectFactory.create(name="Project 1")

    response = graphql(CONNECTION_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": keyset_cursor("Searchable", project_1.pk, __typename="ProjectType"),
                "endCursor": keyset_cursor("Searchable", task_1.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Searchable", project_1.pk, __typename="ProjectType"),
                    "node": {"__typename": "ProjectType", "name": "Project 1"},
                },
                {
                    "cursor": keyset_cursor("Searchable", task_1.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 1"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__last(graphql, undine_settings) -> None:
    """A page taken with 'last' returns the end of the connection."""
    undine_settings.SCHEMA = create_union_schema()

    TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(CONNECTION_QUERY, variables={"last": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
                "endCursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 2"},
                },
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_union_connection__first__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_union_schema()

    task_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")
    project_1 = await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(CONNECTION_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": keyset_cursor("Searchable", project_1.pk, __typename="ProjectType"),
                "endCursor": keyset_cursor("Searchable", task_1.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Searchable", project_1.pk, __typename="ProjectType"),
                    "node": {"__typename": "ProjectType", "name": "Project 1"},
                },
                {
                    "cursor": keyset_cursor("Searchable", task_1.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 1"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__first_and_after(graphql, undine_settings) -> None:
    """Paging with 'first' and 'after' across the union does not crash, and walks the whole connection."""
    undine_settings.SCHEMA = create_union_schema()

    TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(CONNECTION_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    cursor = response.data["searchables"]["pageInfo"]["endCursor"]

    response = graphql(CONNECTION_QUERY, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
                "endCursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 2"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__last_and_before(graphql, undine_settings) -> None:
    """Paging with 'last' and 'before' across the union does not crash, and walks the whole connection."""
    undine_settings.SCHEMA = create_union_schema()

    task_1 = TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    project_1 = ProjectFactory.create(name="Project 1")

    response = graphql(CONNECTION_QUERY, variables={"last": 2})
    assert response.has_errors is False, response.errors

    cursor = response.data["searchables"]["pageInfo"]["startCursor"]
    assert cursor == keyset_cursor("Searchable", task_1.pk, __typename="TaskType")

    response = graphql(CONNECTION_QUERY, variables={"last": 1, "before": cursor})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": keyset_cursor("Searchable", project_1.pk, __typename="ProjectType"),
                "endCursor": keyset_cursor("Searchable", project_1.pk, __typename="ProjectType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Searchable", project_1.pk, __typename="ProjectType"),
                    "node": {"__typename": "ProjectType", "name": "Project 1"},
                },
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_union_connection__first_and_after__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    task_2 = await sync_to_async(TaskFactory.create)(name="Task 2")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(CONNECTION_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    cursor = response.data["searchables"]["pageInfo"]["endCursor"]

    response = await graphql_async(CONNECTION_QUERY, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
                "endCursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Searchable", task_2.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 2"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__cursor_disambiguates_members_with_the_same_primary_key(graphql, undine_settings) -> None:
    """A Task and a Project sharing the same primary key must not produce the same cursor."""
    undine_settings.SCHEMA = create_union_schema()

    task = TaskFactory.create(name="Task 1")
    project = ProjectFactory.create(name="Project 1")
    assert task.pk == project.pk  # Separate auto-increment sequences, so both start at 1.

    response = graphql(CONNECTION_QUERY, variables={"first": 1})
    assert response.has_errors is False, response.errors

    first_cursor = response.data["searchables"]["edges"][0]["cursor"]

    # Paging past the first row must reach the second row, not loop back onto the first one.
    response = graphql(CONNECTION_QUERY, variables={"first": 1, "after": first_cursor})
    assert response.has_errors is False, response.errors

    assert response.data["searchables"]["edges"] == [
        {
            "cursor": keyset_cursor("Searchable", task.pk, __typename="TaskType"),
            "node": {"__typename": "TaskType", "name": "Task 1"},
        },
    ]
    assert response.data["searchables"]["edges"][0]["cursor"] != first_cursor


@pytest.mark.django_db
def test_union_connection__fields_selected_from_one_member_only(graphql, undine_settings) -> None:
    """A member the query selects no fields from is not fetched, not counted, and gets no edges."""
    undine_settings.SCHEMA = create_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables {
            totalCount
            edges { node { ... on TaskType { name } } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 1,
            "edges": [
                {"node": {"name": "Task 1"}},
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__no_fields_selected_from_any_member(graphql, undine_settings) -> None:
    """Selecting only '__typename' selects no fields from any member, so the connection is empty."""
    undine_settings.SCHEMA = create_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables {
            totalCount
            edges { node { __typename } }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": {"totalCount": 0, "edges": []}}
    response.assert_query_count(0)


@pytest.mark.django_db(transaction=True)
async def test_union_connection__no_fields_selected_from_any_member__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          searchables {
            totalCount
            edges { node { __typename } }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": {"totalCount": 0, "edges": []}}


# Filtering


@pytest.mark.django_db
def test_union_connection__filter_per_member(graphql, undine_settings) -> None:
    """Each member of the union can be filtered separately with its own filterset."""

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class ProjectFilterSet(FilterSet[Project], auto=False):
        name = Filter()

    class ProjectType(QueryType[Project], auto=False, filterset=ProjectFilterSet):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")

    query = """
        query {
          searchables(filterTask: {name: "Task 2"}, filterProject: {name: "Project 1"}) {
            totalCount
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "totalCount": 2,
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 2"}},
            ],
        },
    }


def create_filterset_union_schema():
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False):
        name_contains = Filter("name", lookup="icontains")
        starts_with_p = Filter(Q(first_letter="P"), distinct=True)

        @starts_with_p.aliases
        def starts_with_p_aliases(self, info: GQLInfo, *, value: bool) -> dict[str, DjangoExpression]:
            return {"first_letter": Substr("name", 1, 1)}

        @Filter
        def nothing_matches(self, info: GQLInfo, *, value: bool) -> Q:
            raise EmptyFilterResult

    @SearchableFilterSet
    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_union_connection__filter_across_members(graphql, undine_settings) -> None:
    """A filterset on the union type filters every member of the union."""
    undine_settings.SCHEMA = create_filterset_union_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Other")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables(filter: {nameContains: "1"}) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1"}},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_union_connection__filter_across_members__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Other")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          searchables(filter: {nameContains: "1"}) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1"}},
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__filter_not_used(graphql, undine_settings) -> None:
    """A filterset on the union type that is not used leaves the members untouched."""
    undine_settings.SCHEMA = create_filterset_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    response = graphql(NODES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1"}},
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__filter_with_aliases_and_distinct(graphql, undine_settings) -> None:
    """A filter that requires aliases and 'distinct' applies both to every member of the union."""
    undine_settings.SCHEMA = create_filterset_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables(filter: {startsWithP: true}) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__filter_matches_nothing(graphql, undine_settings) -> None:
    """A filter that cannot match anything short-circuits to an empty connection."""
    undine_settings.SCHEMA = create_filterset_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables(filter: {nothingMatches: true}) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": {"edges": []}}


@pytest.mark.django_db(transaction=True)
async def test_union_connection__filter_matches_nothing__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          searchables(filter: {nothingMatches: true}) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": {"edges": []}}


# Ordering


def create_orderset_union_schema():
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False):
        name = Order("name")

        @name.aliases
        def name_aliases(self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]:
            return {"name_lower": Lower("name")}

    @SearchableOrderSet
    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_union_connection__order_across_members(graphql, undine_settings) -> None:
    """An orderset on the union type orders the rows of every member together."""
    undine_settings.SCHEMA = create_orderset_union_schema()

    TaskFactory.create(name="B Task")
    TaskFactory.create(name="D Task")
    ProjectFactory.create(name="A Project")
    ProjectFactory.create(name="C Project")

    query = """
        query {
          searchables(orderBy: nameDesc) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "TaskType", "name": "D Task"}},
                {"node": {"__typename": "ProjectType", "name": "C Project"}},
                {"node": {"__typename": "TaskType", "name": "B Task"}},
                {"node": {"__typename": "ProjectType", "name": "A Project"}},
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__order_not_used(graphql, undine_settings) -> None:
    """An orderset on the union type that is not used leaves the default ordering in place."""
    undine_settings.SCHEMA = create_orderset_union_schema()

    TaskFactory.create(name="B Task")
    ProjectFactory.create(name="A Project")

    response = graphql(NODES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "A Project"}},
                {"node": {"__typename": "TaskType", "name": "B Task"}},
            ],
        },
    }


def create_expression_orderset_union_schema():
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False):
        name_reversed = Order(Reverse("name"))

    @SearchableOrderSet
    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_union_connection__order_across_members__expression(graphql, undine_settings) -> None:
    """
    A union-level order built from an expression (rather than a plain field) needs the expression
    annotated onto every member's queryset, since the combined connection's `ORDER BY` can only
    reference a column, not the original expression.
    """
    undine_settings.SCHEMA = create_expression_orderset_union_schema()

    TaskFactory.create(name="oof")
    ProjectFactory.create(name="rab")

    query = """
        query {
          searchables(orderBy: nameReversedAsc) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "rab"}},
                {"node": {"__typename": "TaskType", "name": "oof"}},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_union_connection__order_across_members__expression__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_expression_orderset_union_schema()

    await sync_to_async(TaskFactory.create)(name="oof")
    await sync_to_async(ProjectFactory.create)(name="rab")

    query = """
        query {
          searchables(orderBy: nameReversedAsc) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "rab"}},
                {"node": {"__typename": "TaskType", "name": "oof"}},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_union_connection__order_across_members__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_orderset_union_schema()

    await sync_to_async(TaskFactory.create)(name="B Task")
    await sync_to_async(ProjectFactory.create)(name="A Project")

    query = """
        query {
          searchables(orderBy: nameDesc) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "TaskType", "name": "B Task"}},
                {"node": {"__typename": "ProjectType", "name": "A Project"}},
            ],
        },
    }


def create_task_points_order_union_schema():
    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()
        points = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_union_connection__order_per_member(graphql, undine_settings) -> None:
    """
    Each member can be given its own orderset. Members are grouped by type (since there's no
    union-level `orderBy` here), and each group is ordered by its own `orderBy<Model>`, but
    groups don't interleave with each other.
    """
    undine_settings.SCHEMA = create_task_points_order_union_schema()

    TaskFactory.create(name="B Task")
    TaskFactory.create(name="A Task")
    ProjectFactory.create(name="C Project")

    query = """
        query {
          searchables(orderByTask: [nameAsc]) {
            edges {
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "C Project"}},
                {"node": {"__typename": "TaskType", "name": "A Task"}},
                {"node": {"__typename": "TaskType", "name": "B Task"}},
            ],
        },
    }


@pytest.mark.django_db
def test_union_connection__last_and_before_with_per_member_order(graphql, undine_settings) -> None:
    """
    'last'/'before' also respects the per-member rank ordering, not just 'first'/'after'.
    Grouped by typename (no union-level order here), 'orderByTask: pointsAsc' orders the Task
    block. Paging backward must land on the same rows 'first'/'after' would.
    """
    undine_settings.SCHEMA = create_task_points_order_union_schema()

    TaskFactory.create(name="T1", points=10)
    TaskFactory.create(name="T2", points=20)
    TaskFactory.create(name="T3", points=30)
    ProjectFactory.create(name="P1")

    query = """
        query Searchables($last: Int, $before: String) {
          searchables(last: $last, before: $before, orderByTask: [pointsAsc]) {
            pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
            edges {
              cursor
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    response = graphql(query, variables={"last": 2})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["searchables"]["edges"]]
    assert names == ["T2", "T3"]

    before_cursor = response.data["searchables"]["edges"][0]["cursor"]

    response = graphql(query, variables={"last": 2, "before": before_cursor})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["searchables"]["edges"]]
    assert names == ["P1", "T1"]


@pytest.mark.django_db
def test_union_connection__insert_before_cursor_with_per_member_order(graphql, undine_settings) -> None:
    """
    The keyset cursor guarantee also holds when a per-member 'orderByTask' puts the rank window
    function in play, not just under the default pk ordering: a row inserted before an already
    fetched page must not shift or duplicate the next page.
    """
    undine_settings.SCHEMA = create_task_points_order_union_schema()

    TaskFactory.create(name="B", points=20)
    TaskFactory.create(name="C", points=30)
    TaskFactory.create(name="D", points=40)
    TaskFactory.create(name="E", points=50)

    query = """
        query Searchables($first: Int, $after: String) {
          searchables(first: $first, after: $after, orderByTask: [pointsAsc]) {
            pageInfo { endCursor }
            edges { node { ... on TaskType { name } } }
          }
        }
    """

    response = graphql(query, variables={"first": 2})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["searchables"]["edges"]]
    assert names == ["B", "C"]
    cursor = response.data["searchables"]["pageInfo"]["endCursor"]

    TaskFactory.create(name="A", points=10)  # Sorts before the page already fetched.

    response = graphql(query, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["searchables"]["edges"]]
    assert names == ["D", "E"]


@pytest.mark.django_db
def test_union_connection__delete_cursor_row_itself(graphql, undine_settings) -> None:
    """Deleting the exact row a cursor points to must not break decoding or paging past it."""
    undine_settings.SCHEMA = create_task_points_order_union_schema()

    TaskFactory.create(name="T1", points=10)
    task_2 = TaskFactory.create(name="T2", points=20)
    TaskFactory.create(name="T3", points=30)

    query = """
        query Searchables($first: Int, $after: String) {
          searchables(first: $first, after: $after, orderByTask: [pointsAsc]) {
            pageInfo { endCursor }
            edges { node { ... on TaskType { name } } }
          }
        }
    """

    response = graphql(query, variables={"first": 2})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["searchables"]["edges"]]
    assert names == ["T1", "T2"]
    cursor = response.data["searchables"]["pageInfo"]["endCursor"]

    task_2.delete()

    response = graphql(query, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["searchables"]["edges"]]
    assert names == ["T3"]


@pytest.mark.django_db
def test_union_connection__full_walk_forward_and_backward(graphql, undine_settings) -> None:
    """
    Grouped by typename (no union-level order here) with 'orderByTask: pointsAsc' ordering the
    Task block (issue 4's rank mechanism), paging forward with 'first' and backward with 'last'
    must both reproduce exactly the same order as an unpaginated query, with no skipped or
    duplicated row, and 'pageInfo' must be fully consistent on every page.
    """
    undine_settings.SCHEMA = create_task_points_order_union_schema()

    TaskFactory.create(name="Task-30", points=30)
    TaskFactory.create(name="Task-10", points=10)
    TaskFactory.create(name="Task-20", points=20)
    ProjectFactory.create(name="Proj-A")
    ProjectFactory.create(name="Proj-B")

    query = """
        query Searchables($first: Int, $last: Int, $after: String, $before: String) {
          searchables(first: $first, last: $last, after: $after, before: $before, orderByTask: [pointsAsc]) {
            pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
            edges {
              cursor
              node {
                __typename
                ... on TaskType { name }
                ... on ProjectType { name }
              }
            }
          }
        }
    """

    def edge_key(edge: dict) -> str:
        return edge["node"]["name"]

    def fetch_page(variables: dict) -> tuple[list[dict], dict]:
        response = graphql(query, variables=variables)
        assert response.has_errors is False, response.errors
        return response.data["searchables"]["edges"], response.data["searchables"]["pageInfo"]

    full_edges, _ = fetch_page({})
    full_names = [edge_key(edge) for edge in full_edges]
    assert full_names == ["Proj-A", "Proj-B", "Task-10", "Task-20", "Task-30"]

    walk_connection_forward_and_backward(
        fetch_page=fetch_page,
        edge_key=edge_key,
        full_edges=full_names,
        page_size=2,
    )


# Permissions


@pytest.mark.django_db
def test_union_connection__entrypoint_permissions(graphql, undine_settings) -> None:
    """The entrypoint permission check runs for every instance in the connection, from every member."""
    seen: list[Any] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

        @searchables.permissions
        def searchables_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            seen.append(value)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    project = ProjectFactory.create(name="Project 1")

    response = graphql(NODES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1"}},
            ],
        },
    }

    assert seen == [project, task]


@pytest.mark.django_db
def test_union_connection__entrypoint_permissions__denied(graphql, undine_settings) -> None:
    """A denied entrypoint permission check surfaces as a GraphQL error."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

        @searchables.permissions
        def searchables_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql(NODES_QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["searchables"],
            },
        ],
    }


@pytest.mark.django_db
def test_union_connection__query_type_permissions__denied(graphql, undine_settings) -> None:
    """A denied query type permission check for a single member surfaces as a GraphQL error."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql(NODES_QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["searchables"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_union_connection__entrypoint_permissions__sync_func__async(graphql_async, undine_settings) -> None:
    """A sync entrypoint permission check also runs on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

        @searchables.permissions
        def searchables_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(NODES_QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["searchables"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_union_connection__entrypoint_permissions__async_func__async(graphql_async, undine_settings) -> None:
    """An async entrypoint permission check is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

        @searchables.permissions
        async def searchables_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(NODES_QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["searchables"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_union_connection__query_type_permissions__async_func__async(graphql_async, undine_settings) -> None:
    """An async query type permission check is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Connection(Searchable))

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(NODES_QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["searchables"],
            },
        ],
    }
