from __future__ import annotations

import operator
from typing import Any

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.db.models.functions import Lower, Substr
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Report, Task
from tests.factories import ProjectFactory, ReportFactory, TaskFactory
from tests.helpers import skip_if_union_queryset_values_broken
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
from undine.pagination import OffsetPagination
from undine.typing import DjangoExpression

NAMED_QUERY = """
    query {
      named {
        __typename
        name
      }
    }
"""


def create_interface_schema(*, limit: int | None = None):
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()
        done = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True, limit=limit)  # type: ignore[arg-type]

    return create_schema(query=Query)


def create_interface_schema_without_implementations():
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class Query(RootType):
        named = Entrypoint(Named, many=True)  # type: ignore[arg-type]

    return create_schema(query=Query)


# Fetching


@pytest.mark.django_db
def test_interface_type__empty(graphql, undine_settings) -> None:
    """With no rows in either implementation, the interface entrypoint returns an empty list."""
    undine_settings.SCHEMA = create_interface_schema()

    response = graphql(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": []}


@pytest.mark.django_db
def test_interface_type__no_implementations(graphql, undine_settings) -> None:
    """An interface no query type implements has nothing to fetch, so the entrypoint returns an empty list."""
    undine_settings.SCHEMA = create_interface_schema_without_implementations()

    response = graphql(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": []}


@pytest.mark.django_db(transaction=True)
async def test_interface_type__no_implementations__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_interface_schema_without_implementations()

    response = await graphql_async(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": []}


@pytest.mark.django_db
def test_interface_type__implementations_not_otherwise_reachable(graphql, undine_settings) -> None:
    """
    Implementations of an interface used by a plain (non-connection) entrypoint do not need an
    `Entrypoint` of their own to be reachable from the schema: `create_schema` forces them in
    regardless.
    """
    undine_settings.SCHEMA = create_interface_schema()

    assert "TaskType" in undine_settings.SCHEMA.type_map
    assert "ProjectType" in undine_settings.SCHEMA.type_map


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__inline_fragment_on_implementation_not_otherwise_reachable(graphql, undine_settings) -> None:
    """An inline fragment on an implementation validates even without an `Entrypoint` for it."""
    undine_settings.SCHEMA = create_interface_schema()

    TaskFactory.create(name="Task 1", done=True)

    query = """
        query {
          named {
            __typename
            ... on TaskType { done }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"__typename": "TaskType", "done": True}]}


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__implementations_across_models(graphql, undine_settings) -> None:
    """Rows from every implementation of the interface are returned, ordered by primary key."""
    undine_settings.SCHEMA = create_interface_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
            {"__typename": "TaskType", "name": "Task 2"},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__implementations_across_models__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_interface_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
            {"__typename": "TaskType", "name": "Task 2"},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__inline_fragments(graphql, undine_settings) -> None:
    """Fields outside the interface are selected with an inline fragment on the implementation."""
    undine_settings.SCHEMA = create_interface_schema()

    TaskFactory.create(name="Task 1", done=True)
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named {
            __typename
            name
            ... on TaskType { done }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1", "done": True},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__fields_selected_from_one_implementation_only(graphql, undine_settings) -> None:
    """An implementation with no fields selected is not fetched at all."""
    undine_settings.SCHEMA = create_interface_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named {
            ... on TaskType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"name": "Task 1"}]}


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__uuid_primary_key(graphql, undine_settings) -> None:
    """An implementation with a UUID primary key is fetched together with integer-keyed ones."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ReportType(QueryType[Report], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    ReportFactory.create(name="Report 1")

    response = graphql(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert sorted(response.data["named"], key=operator.itemgetter("name")) == [
        {"__typename": "ReportType", "name": "Report 1"},
        {"__typename": "TaskType", "name": "Task 1"},
    ]


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__limit(graphql, undine_settings) -> None:
    """The entrypoint limit caps the number of rows returned across all implementations."""
    undine_settings.SCHEMA = create_interface_schema(limit=2)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__limit__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_interface_schema(limit=2)

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


OFFSET_PAGINATED_NAMED_QUERY = """
    query Named($offset: Int, $limit: Int) {
      named(offset: $offset, limit: $limit) {
        __typename
        name
      }
    }
"""


def create_offset_paginated_interface_schema(*, limit: int | None = None):
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(OffsetPagination(Named), limit=limit)  # type: ignore[arg-type]

    return create_schema(query=Query)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__offset_pagination(graphql, undine_settings) -> None:
    """'offset' and 'limit' page the combined result, not the rows of each implementation separately."""
    undine_settings.SCHEMA = create_offset_paginated_interface_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(OFFSET_PAGINATED_NAMED_QUERY, variables={"offset": 1, "limit": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"__typename": "TaskType", "name": "Task 1"}]}


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__offset_pagination__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_offset_paginated_interface_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(OFFSET_PAGINATED_NAMED_QUERY, variables={"offset": 1, "limit": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"__typename": "TaskType", "name": "Task 1"}]}


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__offset_pagination__entrypoint_limit_not_applied(graphql, undine_settings) -> None:
    """An offset paginated entrypoint pages with its own arguments, so its limit doesn't cut the page short."""
    undine_settings.SCHEMA = create_offset_paginated_interface_schema(limit=1)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(OFFSET_PAGINATED_NAMED_QUERY, variables={"limit": 2})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


# Filtering


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__filter_per_implementation(graphql, undine_settings) -> None:
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
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")

    query = """
        query {
          named(filterTask: {name: "Task 2"}, filterProject: {name: "Project 1"}) {
            __typename
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 2"},
        ],
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
        named = Entrypoint(Named, many=True)

    return create_schema(query=Query)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__filter_across_implementations(graphql, undine_settings) -> None:
    """A filterset on the interface filters every implementation."""
    undine_settings.SCHEMA = create_filterset_interface_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Other")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named(filter: {nameContains: "1"}) {
            __typename
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__filter_not_used(graphql, undine_settings) -> None:
    """A filterset on the interface that is not used leaves the implementations untouched."""
    undine_settings.SCHEMA = create_filterset_interface_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    response = graphql(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__filter_with_aliases_and_distinct(graphql, undine_settings) -> None:
    """A filter that requires aliases and 'distinct' applies both to every implementation."""
    undine_settings.SCHEMA = create_filterset_interface_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named(filter: {startsWithP: true}) {
            __typename
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"__typename": "ProjectType", "name": "Project 1"}]}


@pytest.mark.django_db
def test_interface_type__filter_matches_nothing(graphql, undine_settings) -> None:
    """A filter that cannot match anything short-circuits to an empty list."""
    undine_settings.SCHEMA = create_filterset_interface_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          named(filter: {nothingMatches: true}) {
            __typename
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": []}


@pytest.mark.django_db(transaction=True)
async def test_interface_type__filter_matches_nothing__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_interface_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          named(filter: {nothingMatches: true}) {
            __typename
            name
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": []}


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__filter_across_implementations__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_interface_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Other")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          named(filter: {nameContains: "1"}) {
            __typename
            name
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


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
        named = Entrypoint(Named, many=True)

    return create_schema(query=Query)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__order_across_implementations(graphql, undine_settings) -> None:
    """An orderset on the interface orders the rows of every implementation together."""
    undine_settings.SCHEMA = create_orderset_interface_schema()

    TaskFactory.create(name="B Task")
    TaskFactory.create(name="D Task")
    ProjectFactory.create(name="A Project")
    ProjectFactory.create(name="C Project")

    query = """
        query {
          named(orderBy: nameDesc) {
            __typename
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "TaskType", "name": "D Task"},
            {"__typename": "ProjectType", "name": "C Project"},
            {"__typename": "TaskType", "name": "B Task"},
            {"__typename": "ProjectType", "name": "A Project"},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__order_not_used(graphql, undine_settings) -> None:
    """An orderset on the interface that is not used leaves the default ordering in place."""
    undine_settings.SCHEMA = create_orderset_interface_schema()

    TaskFactory.create(name="B Task")
    ProjectFactory.create(name="A Project")

    response = graphql(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "A Project"},
            {"__typename": "TaskType", "name": "B Task"},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__order_across_implementations__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_orderset_interface_schema()

    await sync_to_async(TaskFactory.create)(name="B Task")
    await sync_to_async(ProjectFactory.create)(name="A Project")

    query = """
        query {
          named(orderBy: nameDesc) {
            __typename
            name
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "TaskType", "name": "B Task"},
            {"__typename": "ProjectType", "name": "A Project"},
        ],
    }


def create_filterset_orderset_interface_schema(*, limit: int | None = None):
    class NamedFilterSet(FilterSet[Task, Project], auto=False):
        name_contains = Filter("name", lookup="icontains")

    class NamedOrderSet(OrderSet[Task, Project], auto=False):
        name = Order()

    class Named(InterfaceType, filterset=NamedFilterSet, orderset=NamedOrderSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True, limit=limit)  # type: ignore[arg-type]

    return create_schema(query=Query)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__filter_order_and_limit_combined(graphql, undine_settings) -> None:
    """
    An interface-level filter must be applied before `limit` narrows the result down, not
    after: otherwise `limit` can pick rows that the filter later excludes, dropping matching
    rows instead of returning them. See the open problems file (issue 3).
    """
    undine_settings.SCHEMA = create_filterset_orderset_interface_schema(limit=1)

    TaskFactory.create(name="AAA Other")  # excluded by filter, sorts first
    TaskFactory.create(name="BBB Task 1")  # included, sorts second
    ProjectFactory.create(name="CCC Excluded")  # excluded, sorts third

    query = """
        query {
          named(filter: {nameContains: "1"}, orderBy: nameAsc) {
            __typename
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"__typename": "TaskType", "name": "BBB Task 1"}]}


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__filter_order_and_limit_combined__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_orderset_interface_schema(limit=1)

    await sync_to_async(TaskFactory.create)(name="AAA Other")
    await sync_to_async(TaskFactory.create)(name="BBB Task 1")
    await sync_to_async(ProjectFactory.create)(name="CCC Excluded")

    query = """
        query {
          named(filter: {nameContains: "1"}, orderBy: nameAsc) {
            __typename
            name
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"__typename": "TaskType", "name": "BBB Task 1"}]}


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__order_per_implementation(graphql, undine_settings) -> None:
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
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="B Task")
    TaskFactory.create(name="A Task")
    ProjectFactory.create(name="C Project")

    query = """
        query {
          named(orderByTask: [nameAsc]) {
            __typename
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "C Project"},
            {"__typename": "TaskType", "name": "A Task"},
            {"__typename": "TaskType", "name": "B Task"},
        ],
    }


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__limit_with_per_implementation_order(graphql, undine_settings) -> None:
    """
    'limit' must slice the queryset built from the final per-implementation rank order (issue 4),
    not a differently-ordered one, on the plain (non-connection) list resolver too (issue 3).
    """

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskOrderSet(OrderSet[Task], auto=False):
        points = Order()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False, orderset=TaskOrderSet):
        name = Field()
        points = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True, limit=2)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="T-low", points=1)
    TaskFactory.create(name="T-high", points=99)
    ProjectFactory.create(name="P1")

    query = """
        query {
          named(orderByTask: [pointsDesc]) {
            __typename
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # Grouped by typename (no interface-level order) -> Project block first, then Task block by
    # pointsDesc; limit=2 takes the first two rows of that order: [P1, T-high].
    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "P1"},
            {"__typename": "TaskType", "name": "T-high"},
        ],
    }


# Permissions


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__entrypoint_permissions(graphql, undine_settings) -> None:
    """The entrypoint permission check runs for every instance from every implementation."""
    seen: list[Any] = []

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        @named.permissions
        def named_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            seen.append(value)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    project = ProjectFactory.create(name="Project 1")

    response = graphql(NAMED_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }

    assert seen == [project, task]


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__entrypoint_permissions__denied(graphql, undine_settings) -> None:
    """A denied entrypoint permission check surfaces as a GraphQL error."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        @named.permissions
        def named_permissions(self, info: GQLInfo, value: Task) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql(NAMED_QUERY)

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


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__query_type_permissions__denied(graphql, undine_settings) -> None:
    """A denied query type permission check for a single implementation surfaces as a GraphQL error."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql(NAMED_QUERY)

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


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__entrypoint_permissions__sync_func__async(graphql_async, undine_settings) -> None:
    """A sync entrypoint permission check also runs on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        @named.permissions
        def named_permissions(self, info: GQLInfo, value: Task) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(NAMED_QUERY)

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


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__entrypoint_permissions__async_func__async(graphql_async, undine_settings) -> None:
    """An async entrypoint permission check is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        @named.permissions
        async def named_permissions(self, info: GQLInfo, value: Task) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(NAMED_QUERY)

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


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__query_type_permissions__sync_func__async(graphql_async, undine_settings) -> None:
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

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(NAMED_QUERY)

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


@skip_if_union_queryset_values_broken
@pytest.mark.django_db(transaction=True)
async def test_interface_type__query_type_permissions__async_func__async(graphql_async, undine_settings) -> None:
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

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(NAMED_QUERY)

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
