from __future__ import annotations

import operator
from typing import Any

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.db.models.functions import Lower, Reverse, Substr
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Report, Task
from tests.factories import ProjectFactory, ReportFactory, TaskFactory
from tests.helpers import keyset_cursor, walk_connection_forward_and_backward
from undine import (
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    InterfaceField,
    InterfaceType,
    Order,
    OrderSet,
    QueryType,
    RootType,
    create_schema,
)
from undine.exceptions import EmptyFilterResult, GraphQLPermissionError
from undine.relay import Connection
from undine.typing import DjangoExpression

CONNECTION_QUERY = """
    query {
      named {
        totalCount
        pageInfo { hasNextPage hasPreviousPage }
        edges { node { name } }
      }
    }
"""

PAGE_QUERY = """
    query Named($first: Int, $last: Int, $after: String, $before: String) {
      named(first: $first, last: $last, after: $after, before: $before) {
        totalCount
        pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
        edges {
          cursor
          node { __typename name }
        }
      }
    }
"""

NODES_QUERY = """
    query {
      named {
        edges { node { __typename name } }
      }
    }
"""


def create_schema_without_implementations():
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    return create_schema(query=Query)


def create_schema_with_implementations():
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()
        done = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    return create_schema(query=Query)


# Paging


@pytest.mark.django_db
def test_interface_connection__no_implementations(graphql, undine_settings) -> None:
    """An interface no query type implements has nothing to fetch, so the connection is empty."""
    undine_settings.SCHEMA = create_schema_without_implementations()

    response = graphql(CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 0,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False},
            "edges": [],
        }
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__no_implementations__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema_without_implementations()

    response = await graphql_async(CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 0,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False},
            "edges": [],
        }
    }


@pytest.mark.django_db
def test_interface_connection__implementations_not_otherwise_reachable(graphql, undine_settings) -> None:
    """
    Implementations of an interface used by a connection do not need an `Entrypoint` of their own
    to be reachable from the schema: `create_schema` forces them in regardless.
    """
    undine_settings.SCHEMA = create_schema_with_implementations()

    assert "TaskType" in undine_settings.SCHEMA.type_map
    assert "ProjectType" in undine_settings.SCHEMA.type_map


@pytest.mark.django_db
def test_interface_connection__inline_fragment_on_implementation_not_otherwise_reachable(
    graphql, undine_settings
) -> None:
    """An inline fragment on an implementation validates even without an `Entrypoint` for it."""
    undine_settings.SCHEMA = create_schema_with_implementations()

    TaskFactory.create(name="Task 1", done=True)

    query = """
        query {
          named {
            edges { node { __typename ... on TaskType { done } } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "TaskType", "done": True}},
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__implementations_across_models(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = create_schema_with_implementations()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    response = graphql(CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data["named"]["totalCount"] == 2
    assert sorted(edge["node"]["name"] for edge in response.data["named"]["edges"]) == ["Project 1", "Task 1"]


@pytest.mark.django_db
def test_interface_connection__no_rows(graphql, undine_settings) -> None:
    """An interface whose implementations have no rows resolves to an empty connection."""
    undine_settings.SCHEMA = create_schema_with_implementations()

    response = graphql(PAGE_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
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
def test_interface_connection__implementation_with_no_rows(graphql, undine_settings) -> None:
    """An implementation that contributes no rows does not add edges, but the others still resolve."""
    undine_settings.SCHEMA = create_schema_with_implementations()

    task = TaskFactory.create(name="Task 1")

    response = graphql(PAGE_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 1,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": keyset_cursor("Named", task.pk, __typename="TaskType"),
                "endCursor": keyset_cursor("Named", task.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Named", task.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 1"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__first(graphql, undine_settings) -> None:
    """A page taken with 'first' spans all implementations, and 'totalCount' counts rows in all of them."""
    undine_settings.SCHEMA = create_schema_with_implementations()

    task_1 = TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    project_1 = ProjectFactory.create(name="Project 1")

    response = graphql(PAGE_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": keyset_cursor("Named", project_1.pk, __typename="ProjectType"),
                "endCursor": keyset_cursor("Named", task_1.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Named", project_1.pk, __typename="ProjectType"),
                    "node": {"__typename": "ProjectType", "name": "Project 1"},
                },
                {
                    "cursor": keyset_cursor("Named", task_1.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 1"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__last(graphql, undine_settings) -> None:
    """A page taken with 'last' returns the end of the connection."""
    undine_settings.SCHEMA = create_schema_with_implementations()

    TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(PAGE_QUERY, variables={"last": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
                "endCursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 2"},
                },
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__first__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema_with_implementations()

    task_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")
    project_1 = await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(PAGE_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": keyset_cursor("Named", project_1.pk, __typename="ProjectType"),
                "endCursor": keyset_cursor("Named", task_1.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Named", project_1.pk, __typename="ProjectType"),
                    "node": {"__typename": "ProjectType", "name": "Project 1"},
                },
                {
                    "cursor": keyset_cursor("Named", task_1.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 1"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__first_and_after(graphql, undine_settings) -> None:
    """Paging with 'first' and 'after' across implementations does not crash, and walks the whole connection."""
    undine_settings.SCHEMA = create_schema_with_implementations()

    TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(PAGE_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    cursor = response.data["named"]["pageInfo"]["endCursor"]

    response = graphql(PAGE_QUERY, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
                "endCursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 2"},
                },
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__first_and_after__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema_with_implementations()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    task_2 = await sync_to_async(TaskFactory.create)(name="Task 2")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(PAGE_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    cursor = response.data["named"]["pageInfo"]["endCursor"]

    response = await graphql_async(PAGE_QUERY, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
                "endCursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
            },
            "edges": [
                {
                    "cursor": keyset_cursor("Named", task_2.pk, __typename="TaskType"),
                    "node": {"__typename": "TaskType", "name": "Task 2"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__cursor_disambiguates_implementations_with_the_same_primary_key(
    graphql, undine_settings
) -> None:
    """A Task and a Project sharing the same primary key must not produce the same cursor."""
    undine_settings.SCHEMA = create_schema_with_implementations()

    task = TaskFactory.create(name="Task 1")
    project = ProjectFactory.create(name="Project 1")
    assert task.pk == project.pk  # Separate auto-increment sequences, so both start at 1.

    response = graphql(PAGE_QUERY, variables={"first": 1})
    assert response.has_errors is False, response.errors

    first_cursor = response.data["named"]["edges"][0]["cursor"]

    # Paging past the first row must reach the second row, not loop back onto the first one.
    response = graphql(PAGE_QUERY, variables={"first": 1, "after": first_cursor})
    assert response.has_errors is False, response.errors

    assert response.data["named"]["edges"] == [
        {
            "cursor": keyset_cursor("Named", task.pk, __typename="TaskType"),
            "node": {"__typename": "TaskType", "name": "Task 1"},
        },
    ]
    assert response.data["named"]["edges"][0]["cursor"] != first_cursor


@pytest.mark.django_db
def test_interface_connection__inline_fragments(graphql, undine_settings) -> None:
    """Fields outside the interface are selected with an inline fragment on the implementation."""
    undine_settings.SCHEMA = create_schema_with_implementations()

    TaskFactory.create(name="Task 1", done=True)
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named {
            edges {
              node {
                __typename
                name
                ... on TaskType { done }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1", "done": True}},
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__uuid_primary_key(graphql, undine_settings) -> None:
    """An implementation with a UUID primary key is paginated together with integer-keyed ones."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ReportType(QueryType[Report], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    ReportFactory.create(name="Report 1")

    response = graphql(NODES_QUERY)
    assert response.has_errors is False, response.errors

    nodes = [edge["node"] for edge in response.data["named"]["edges"]]
    assert sorted(nodes, key=operator.itemgetter("name")) == [
        {"__typename": "ReportType", "name": "Report 1"},
        {"__typename": "TaskType", "name": "Task 1"},
    ]


# Filtering


@pytest.mark.django_db
def test_interface_connection__filter_per_implementation(graphql, undine_settings) -> None:
    """Each implementation can be filtered separately with its own filterset."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False, filterset=TaskFilterSet):
        name = Field()

    class ProjectFilterSet(FilterSet[Project], auto=False):
        name = Filter()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False, filterset=ProjectFilterSet):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")

    query = """
        query {
          named(filterTask: {name: "Task 2"}, filterProject: {name: "Project 1"}) {
            totalCount
            edges { node { __typename name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 2,
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 2"}},
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__total_count_one_implementation_all_filtered(graphql, undine_settings) -> None:
    """'totalCount' still reflects the other implementation when a per-implementation filter excludes all of one."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False, filterset=TaskFilterSet):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")

    query = """
        query {
          named(filterTask: {name: "No such task"}) {
            totalCount
            edges { node { __typename name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "totalCount": 2,
            "edges": [
                {"node": {"__typename": "ProjectType", "name": project_1.name}},
                {"node": {"__typename": "ProjectType", "name": project_2.name}},
            ],
        },
    }


def create_filterset_interface_schema():
    class NamedFilterSet(FilterSet[Task, Project], auto=False):
        name_contains = Filter("name", lookup="icontains")
        starts_with_p = Filter(Q(first_letter="P"), distinct=True, field_name="name")

        @starts_with_p.aliases
        def starts_with_p_aliases(self, info: GQLInfo, *, value: bool) -> dict[str, DjangoExpression]:
            return {"first_letter": Substr("name", 1, 1)}

        @Filter(field_name="name")
        def nothing_matches(self, info: GQLInfo, *, value: bool) -> Q:
            raise EmptyFilterResult

    class Named(InterfaceType, filterset=NamedFilterSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_interface_connection__filter_across_implementations(graphql, undine_settings) -> None:
    """A filterset on the interface filters every implementation."""
    undine_settings.SCHEMA = create_filterset_interface_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Other")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named(filter: {nameContains: "1"}) {
            edges { node { __typename name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1"}},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__filter_across_implementations__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_interface_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Other")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          named(filter: {nameContains: "1"}) {
            edges { node { __typename name } }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1"}},
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__filter_not_used(graphql, undine_settings) -> None:
    """A filterset on the interface that is not used leaves the implementations untouched."""
    undine_settings.SCHEMA = create_filterset_interface_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    response = graphql(NODES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1"}},
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__filter_with_aliases_and_distinct(graphql, undine_settings) -> None:
    """A filter that requires aliases and 'distinct' applies both to every implementation."""
    undine_settings.SCHEMA = create_filterset_interface_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named(filter: {startsWithP: true}) {
            edges { node { __typename name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__filter_matches_nothing(graphql, undine_settings) -> None:
    """A filter that cannot match anything short-circuits to an empty connection."""
    undine_settings.SCHEMA = create_filterset_interface_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named(filter: {nothingMatches: true}) {
            edges { node { __typename name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": {"edges": []}}


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__filter_matches_nothing__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_interface_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          named(filter: {nothingMatches: true}) {
            edges { node { __typename name } }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": {"edges": []}}


# Ordering


def create_orderset_interface_schema():
    class NamedOrderSet(OrderSet[Task, Project], auto=False):
        name = Order("name")

        @name.aliases
        def name_aliases(self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]:
            return {"name_lower": Lower("name")}

    class Named(InterfaceType, orderset=NamedOrderSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_interface_connection__order_across_implementations(graphql, undine_settings) -> None:
    """An orderset on the interface orders the rows of every implementation together."""
    undine_settings.SCHEMA = create_orderset_interface_schema()

    TaskFactory.create(name="B Task")
    TaskFactory.create(name="D Task")
    ProjectFactory.create(name="A Project")
    ProjectFactory.create(name="C Project")

    query = """
        query {
          named(orderBy: nameDesc) {
            edges { node { __typename name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "TaskType", "name": "D Task"}},
                {"node": {"__typename": "ProjectType", "name": "C Project"}},
                {"node": {"__typename": "TaskType", "name": "B Task"}},
                {"node": {"__typename": "ProjectType", "name": "A Project"}},
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__order_not_used(graphql, undine_settings) -> None:
    """An orderset on the interface that is not used leaves the default ordering in place."""
    undine_settings.SCHEMA = create_orderset_interface_schema()

    TaskFactory.create(name="B Task")
    ProjectFactory.create(name="A Project")

    response = graphql(NODES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "A Project"}},
                {"node": {"__typename": "TaskType", "name": "B Task"}},
            ],
        },
    }


def create_expression_orderset_interface_schema():
    class NamedOrderSet(OrderSet[Task, Project], auto=False):
        name_reversed = Order(Reverse("name"), field_name="name")

    class Named(InterfaceType, orderset=NamedOrderSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_interface_connection__order_across_implementations__expression(graphql, undine_settings) -> None:
    """
    An interface-level order built from an expression (rather than a plain field) needs the
    expression annotated onto every implementation's queryset, since the combined connection's
    `ORDER BY` can only reference a column, not the original expression.
    """
    undine_settings.SCHEMA = create_expression_orderset_interface_schema()

    TaskFactory.create(name="oof")
    ProjectFactory.create(name="rab")

    query = """
        query {
          named(orderBy: nameReversedAsc) {
            edges { node { __typename name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "rab"}},
                {"node": {"__typename": "TaskType", "name": "oof"}},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__order_across_implementations__expression__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_expression_orderset_interface_schema()

    await sync_to_async(TaskFactory.create)(name="oof")
    await sync_to_async(ProjectFactory.create)(name="rab")

    query = """
        query {
          named(orderBy: nameReversedAsc) {
            edges { node { __typename name } }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "rab"}},
                {"node": {"__typename": "TaskType", "name": "oof"}},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__order_across_implementations__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_orderset_interface_schema()

    await sync_to_async(TaskFactory.create)(name="B Task")
    await sync_to_async(ProjectFactory.create)(name="A Project")

    query = """
        query {
          named(orderBy: nameDesc) {
            edges { node { __typename name } }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "TaskType", "name": "B Task"}},
                {"node": {"__typename": "ProjectType", "name": "A Project"}},
            ],
        },
    }


@pytest.mark.django_db
def test_interface_connection__order_per_implementation(graphql, undine_settings) -> None:
    """
    Each implementation can be given its own orderset. Implementations are grouped by type
    (since there's no interface-level `orderBy` here), and each group is ordered by its own
    `orderBy<Model>`, but groups don't interleave with each other.
    """

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False, orderset=TaskOrderSet):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="B Task")
    TaskFactory.create(name="A Task")
    ProjectFactory.create(name="C Project")

    query = """
        query {
          named(orderByTask: [nameAsc]) {
            edges { node { __typename name } }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "C Project"}},
                {"node": {"__typename": "TaskType", "name": "A Task"}},
                {"node": {"__typename": "TaskType", "name": "B Task"}},
            ],
        },
    }


def create_task_points_order_interface_schema():
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()
        points = Order()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False, orderset=TaskOrderSet):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_interface_connection__last_and_before_with_per_implementation_order(graphql, undine_settings) -> None:
    """
    'last'/'before' also respects the per-implementation rank ordering (issue 4), not just
    'first'/'after'. Grouped by typename (no interface-level order here), 'orderByTask: pointsAsc'
    orders the Task block; paging backward must land on the same rows 'first'/'after' would.
    """
    undine_settings.SCHEMA = create_task_points_order_interface_schema()

    TaskFactory.create(name="T1", points=10)
    TaskFactory.create(name="T2", points=20)
    TaskFactory.create(name="T3", points=30)
    ProjectFactory.create(name="P1")

    query = """
        query Named($last: Int, $before: String) {
          named(last: $last, before: $before, orderByTask: [pointsAsc]) {
            pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
            edges { cursor node { __typename name } }
          }
        }
    """

    response = graphql(query, variables={"last": 2})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["named"]["edges"]]
    assert names == ["T2", "T3"]

    before_cursor = response.data["named"]["edges"][0]["cursor"]

    response = graphql(query, variables={"last": 2, "before": before_cursor})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["named"]["edges"]]
    assert names == ["P1", "T1"]


@pytest.mark.django_db
def test_interface_connection__insert_before_cursor_with_per_implementation_order(graphql, undine_settings) -> None:
    """
    The keyset cursor guarantee (issue 5) also holds when a per-implementation 'orderByTask'
    puts the rank window function (issue 4) in play, not just under the default pk ordering:
    a row inserted before an already-fetched page must not shift or duplicate the next page.
    """
    undine_settings.SCHEMA = create_task_points_order_interface_schema()

    TaskFactory.create(name="B", points=20)
    TaskFactory.create(name="C", points=30)
    TaskFactory.create(name="D", points=40)
    TaskFactory.create(name="E", points=50)

    query = """
        query Named($first: Int, $after: String) {
          named(first: $first, after: $after, orderByTask: [pointsAsc]) {
            pageInfo { endCursor }
            edges { node { name } }
          }
        }
    """

    response = graphql(query, variables={"first": 2})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["named"]["edges"]]
    assert names == ["B", "C"]
    cursor = response.data["named"]["pageInfo"]["endCursor"]

    TaskFactory.create(name="A", points=10)  # Sorts before the page already fetched.

    response = graphql(query, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["named"]["edges"]]
    assert names == ["D", "E"]


@pytest.mark.django_db
def test_interface_connection__delete_cursor_row_itself(graphql, undine_settings) -> None:
    """Deleting the exact row a cursor points to must not break decoding or paging past it."""
    undine_settings.SCHEMA = create_task_points_order_interface_schema()

    TaskFactory.create(name="T1", points=10)
    task_2 = TaskFactory.create(name="T2", points=20)
    TaskFactory.create(name="T3", points=30)

    query = """
        query Named($first: Int, $after: String) {
          named(first: $first, after: $after, orderByTask: [pointsAsc]) {
            edges { node { name } }
            pageInfo { endCursor }
          }
        }
    """

    response = graphql(query, variables={"first": 2})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["named"]["edges"]]
    assert names == ["T1", "T2"]
    cursor = response.data["named"]["pageInfo"]["endCursor"]

    task_2.delete()

    response = graphql(query, variables={"first": 2, "after": cursor})
    assert response.has_errors is False, response.errors

    names = [edge["node"]["name"] for edge in response.data["named"]["edges"]]
    assert names == ["T3"]


def create_shared_and_member_order_interface_schema():
    class NamedOrderSet(OrderSet[Task, Project], auto=False):
        name = Order()

    class Named(InterfaceType, orderset=NamedOrderSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskOrderSet(OrderSet[Task], auto=False):
        points = Order()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False, orderset=TaskOrderSet):
        name = Field()
        points = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_interface_connection__full_walk_forward_and_backward(graphql, undine_settings) -> None:
    """
    Rows of different implementations that tie on the interface-level order value (here 'name')
    are broken by '__typename' first, then by the per-implementation order (here 'points' desc
    on Task, per issue 4's rank mechanism) - and paging forward and backward through the tie
    lands on exactly the same rows and order as an unpaginated query, with 'pageInfo' fully
    consistent on every page.
    """
    undine_settings.SCHEMA = create_shared_and_member_order_interface_schema()

    TaskFactory.create(name="Same", points=5)
    TaskFactory.create(name="Same", points=15)
    ProjectFactory.create(name="Same")
    TaskFactory.create(name="Zeta", points=1)

    query = """
        query Named($first: Int, $last: Int, $after: String, $before: String) {
          named(
            first: $first, last: $last, after: $after, before: $before, orderBy: nameAsc, orderByTask: [pointsDesc]
          ) {
            pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
            edges { cursor node { __typename name ... on TaskType { points } } }
          }
        }
    """

    def edge_key(edge: dict) -> tuple:
        node = edge["node"]
        return node["__typename"], node["name"], node.get("points")

    def fetch_page(variables: dict) -> tuple[list[dict], dict]:
        response = graphql(query, variables=variables)
        assert response.has_errors is False, response.errors
        return response.data["named"]["edges"], response.data["named"]["pageInfo"]

    full_edges_raw, _ = fetch_page({})
    full_edges = [edge_key(edge) for edge in full_edges_raw]
    assert full_edges == [
        ("ProjectType", "Same", None),
        ("TaskType", "Same", 15),
        ("TaskType", "Same", 5),
        ("TaskType", "Zeta", 1),
    ]

    walk_connection_forward_and_backward(
        fetch_page=fetch_page,
        edge_key=edge_key,
        full_edges=full_edges,
        page_size=1,
    )


# Permissions


@pytest.mark.django_db
def test_interface_connection__entrypoint_permissions(graphql, undine_settings) -> None:
    """The entrypoint permission check runs for every instance in the connection, from every implementation."""
    seen: list[Any] = []

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

        @named.permissions
        def named_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            seen.append(value)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    project = ProjectFactory.create(name="Project 1")

    response = graphql(NODES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": {
            "edges": [
                {"node": {"__typename": "ProjectType", "name": "Project 1"}},
                {"node": {"__typename": "TaskType", "name": "Task 1"}},
            ],
        },
    }

    assert seen == [project, task]


@pytest.mark.django_db
def test_interface_connection__entrypoint_permissions__denied(graphql, undine_settings) -> None:
    """A denied entrypoint permission check surfaces as a GraphQL error."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

        @named.permissions
        def named_permissions(self, info: GQLInfo, value: Task | Project) -> None:
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
                "path": ["named"],
            },
        ],
    }


@pytest.mark.django_db
def test_interface_connection__query_type_permissions__denied(graphql, undine_settings) -> None:
    """A denied query type permission check for a single implementation surfaces as a GraphQL error."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

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
                "path": ["named"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__entrypoint_permissions__sync_func__async(graphql_async, undine_settings) -> None:
    """A sync entrypoint permission check also runs on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

        @named.permissions
        def named_permissions(self, info: GQLInfo, value: Task | Project) -> None:
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
                "path": ["named"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__entrypoint_permissions__async_func__async(graphql_async, undine_settings) -> None:
    """An async entrypoint permission check is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

        @named.permissions
        async def named_permissions(self, info: GQLInfo, value: Task | Project) -> None:
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
                "path": ["named"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__query_type_permissions__sync_func__async(graphql_async, undine_settings) -> None:
    """A sync query type permission check also runs on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

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
                "path": ["named"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_interface_connection__query_type_permissions__async_func__async(graphql_async, undine_settings) -> None:
    """An async query type permission check is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Connection(Named))

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
                "path": ["named"],
            },
        ],
    }
