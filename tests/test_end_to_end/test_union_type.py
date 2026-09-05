from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.db.models.functions import Lower, Substr

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
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
from undine.pagination import OffsetPagination
from undine.typing import DjangoExpression

SEARCHABLES_QUERY = """
    query {
      searchables {
        __typename
        ... on TaskType { name }
        ... on ProjectType { name }
      }
    }
"""


def create_union_schema(*, limit: int | None = None):
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True, limit=limit)  # type: ignore[arg-type]

    return create_schema(query=Query)


# Fetching


@pytest.mark.django_db
def test_union_type__empty(graphql, undine_settings) -> None:
    """With no rows in either member model, the union entrypoint returns an empty list."""
    undine_settings.SCHEMA = create_union_schema()

    response = graphql(SEARCHABLES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": []}


@pytest.mark.django_db
def test_union_type__typename_only_no_matching_fragment(graphql, undine_settings) -> None:
    """
    Selecting only `__typename`, with no inline fragment for either member, selects nothing from
    either member's query type, so the union entrypoint has nothing to fetch and returns an empty
    list, even though rows exist for both members.
    """
    undine_settings.SCHEMA = create_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    response = graphql("query { searchables { __typename } }")
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": []}


@pytest.mark.django_db(transaction=True)
async def test_union_type__typename_only_no_matching_fragment__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async("query { searchables { __typename } }")
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": []}


@pytest.mark.django_db
def test_union_type__both_members(graphql, undine_settings) -> None:
    """Rows from both members of the union are returned, ordered by primary key."""
    undine_settings.SCHEMA = create_union_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(SEARCHABLES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
            {"__typename": "TaskType", "name": "Task 2"},
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_union_type__both_members__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(SEARCHABLES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
            {"__typename": "TaskType", "name": "Task 2"},
        ],
    }


@pytest.mark.django_db
def test_union_type__fields_selected_from_one_member_only(graphql, undine_settings) -> None:
    """A member with no fields selected is not fetched at all."""
    undine_settings.SCHEMA = create_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables {
            ... on TaskType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": [{"name": "Task 1"}]}


@pytest.mark.django_db
def test_union_type__limit(graphql, undine_settings) -> None:
    """The entrypoint limit caps the number of rows returned across all members of the union."""
    undine_settings.SCHEMA = create_union_schema(limit=2)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(SEARCHABLES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_union_type__limit__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_union_schema(limit=2)

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(SEARCHABLES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


OFFSET_PAGINATED_SEARCHABLES_QUERY = """
    query Searchables($offset: Int, $limit: Int) {
      searchables(offset: $offset, limit: $limit) {
        __typename
        ... on TaskType { name }
        ... on ProjectType { name }
      }
    }
"""


def create_offset_paginated_union_schema(*, limit: int | None = None):
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(OffsetPagination(Searchable), limit=limit)  # type: ignore[arg-type]

    return create_schema(query=Query)


@pytest.mark.django_db
def test_union_type__offset_pagination(graphql, undine_settings) -> None:
    """'offset' and 'limit' page the combined result, not the rows of each member separately."""
    undine_settings.SCHEMA = create_offset_paginated_union_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(OFFSET_PAGINATED_SEARCHABLES_QUERY, variables={"offset": 1, "limit": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": [{"__typename": "TaskType", "name": "Task 1"}]}


@pytest.mark.django_db(transaction=True)
async def test_union_type__offset_pagination__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_offset_paginated_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    response = await graphql_async(OFFSET_PAGINATED_SEARCHABLES_QUERY, variables={"offset": 1, "limit": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": [{"__typename": "TaskType", "name": "Task 1"}]}


@pytest.mark.django_db
def test_union_type__offset_pagination__entrypoint_limit_not_applied(graphql, undine_settings) -> None:
    """An offset paginated entrypoint pages with its own arguments, so its limit doesn't cut the page short."""
    undine_settings.SCHEMA = create_offset_paginated_union_schema(limit=1)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")

    response = graphql(OFFSET_PAGINATED_SEARCHABLES_QUERY, variables={"limit": 2})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


# Filtering


@pytest.mark.django_db
def test_union_type__filter_per_member(graphql, undine_settings) -> None:
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
        searchables = Entrypoint(Searchable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")

    query = """
        query {
          searchables(filterTask: {name: "Task 2"}, filterProject: {name: "Project 1"}) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 2"},
        ],
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
        searchables = Entrypoint(Searchable, many=True)

    return create_schema(query=Query)


@pytest.mark.django_db
def test_union_type__filter_across_members(graphql, undine_settings) -> None:
    """A filterset on the union type filters every member of the union."""
    undine_settings.SCHEMA = create_filterset_union_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Other")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables(filter: {nameContains: "1"}) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


@pytest.mark.django_db
def test_union_type__filter_not_used(graphql, undine_settings) -> None:
    """A filterset on the union type that is not used leaves the members untouched."""
    undine_settings.SCHEMA = create_filterset_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    response = graphql(SEARCHABLES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


@pytest.mark.django_db
def test_union_type__filter_with_aliases_and_distinct(graphql, undine_settings) -> None:
    """A filter that requires aliases and 'distinct' applies both to every member of the union."""
    undine_settings.SCHEMA = create_filterset_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables(filter: {startsWithP: true}) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": [{"__typename": "ProjectType", "name": "Project 1"}]}


@pytest.mark.django_db
def test_union_type__filter_matches_nothing(graphql, undine_settings) -> None:
    """A filter that cannot match anything short-circuits to an empty list."""
    undine_settings.SCHEMA = create_filterset_union_schema()

    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")

    query = """
        query {
          searchables(filter: {nothingMatches: true}) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": []}


@pytest.mark.django_db(transaction=True)
async def test_union_type__filter_matches_nothing__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          searchables(filter: {nothingMatches: true}) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": []}


@pytest.mark.django_db(transaction=True)
async def test_union_type__filter_across_members__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_union_schema()

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Other")
    await sync_to_async(ProjectFactory.create)(name="Project 1")

    query = """
        query {
          searchables(filter: {nameContains: "1"}) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }


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
        searchables = Entrypoint(Searchable, many=True)

    return create_schema(query=Query)


@pytest.mark.django_db
def test_union_type__order_across_members(graphql, undine_settings) -> None:
    """An orderset on the union type orders the rows of every member together."""
    undine_settings.SCHEMA = create_orderset_union_schema()

    TaskFactory.create(name="B Task")
    TaskFactory.create(name="D Task")
    ProjectFactory.create(name="A Project")
    ProjectFactory.create(name="C Project")

    query = """
        query {
          searchables(orderBy: nameDesc) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "TaskType", "name": "D Task"},
            {"__typename": "ProjectType", "name": "C Project"},
            {"__typename": "TaskType", "name": "B Task"},
            {"__typename": "ProjectType", "name": "A Project"},
        ],
    }


@pytest.mark.django_db
def test_union_type__order_not_used(graphql, undine_settings) -> None:
    """An orderset on the union type that is not used leaves the default ordering in place."""
    undine_settings.SCHEMA = create_orderset_union_schema()

    TaskFactory.create(name="B Task")
    ProjectFactory.create(name="A Project")

    response = graphql(SEARCHABLES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "A Project"},
            {"__typename": "TaskType", "name": "B Task"},
        ],
    }


@pytest.mark.django_db
def test_union_type__order_per_implementation(graphql, undine_settings) -> None:
    """
    Each member can be given its own orderset. Members are grouped by type (since there's no
    union-level `orderBy` here), and each group is ordered by its own `orderBy<Model>`, but
    groups don't interleave with each other.
    """

    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="B Task")
    TaskFactory.create(name="A Task")
    ProjectFactory.create(name="C Project")

    query = """
        query {
          searchables(orderByTask: [nameAsc]) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "C Project"},
            {"__typename": "TaskType", "name": "A Task"},
            {"__typename": "TaskType", "name": "B Task"},
        ],
    }


@pytest.mark.django_db
def test_union_type__limit_with_per_implementation_order(graphql, undine_settings) -> None:
    """
    'limit' must slice the queryset built from the final per-implementation rank order (issue 4),
    not a differently-ordered one, on the plain (non-connection) list resolver too (issue 3).
    """

    class TaskOrderSet(OrderSet[Task], auto=False):
        points = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        points = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True, limit=2)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="T-low", points=1)
    TaskFactory.create(name="T-high", points=99)
    ProjectFactory.create(name="P1")

    query = """
        query {
          searchables(orderByTask: [pointsDesc]) {
            __typename
            ... on TaskType { name points }
            ... on ProjectType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # Grouped by typename (no union-level order) -> Project block first, then Task block by
    # pointsDesc; limit=2 takes the first two rows of that order: [P1, T-high].
    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "P1"},
            {"__typename": "TaskType", "name": "T-high", "points": 99},
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_union_type__order_across_members__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_orderset_union_schema()

    await sync_to_async(TaskFactory.create)(name="B Task")
    await sync_to_async(ProjectFactory.create)(name="A Project")

    query = """
        query {
          searchables(orderBy: nameDesc) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "TaskType", "name": "B Task"},
            {"__typename": "ProjectType", "name": "A Project"},
        ],
    }


def create_filterset_orderset_union_schema(*, limit: int | None = None):
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False):
        name_contains = Filter("name", lookup="icontains")

    class SearchableOrderSet(OrderSet[Task, Project], auto=False):
        name = Order()

    @SearchableFilterSet
    @SearchableOrderSet
    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True, limit=limit)  # type: ignore[arg-type]

    return create_schema(query=Query)


@pytest.mark.django_db
def test_union_type__filter_order_and_limit_combined(graphql, undine_settings) -> None:
    """
    A union/interface-level filter must be applied before `limit` narrows the result down,
    not after: otherwise `limit` can pick rows that the filter later excludes, dropping
    matching rows instead of returning them. See the open problems file (issue 3).
    """
    undine_settings.SCHEMA = create_filterset_orderset_union_schema(limit=1)

    TaskFactory.create(name="AAA Other")  # excluded by filter, sorts first
    TaskFactory.create(name="BBB Task 1")  # included, sorts second
    ProjectFactory.create(name="CCC Excluded")  # excluded, sorts third

    query = """
        query {
          searchables(filter: {nameContains: "1"}, orderBy: nameAsc) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": [{"__typename": "TaskType", "name": "BBB Task 1"}]}


@pytest.mark.django_db(transaction=True)
async def test_union_type__filter_order_and_limit_combined__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_filterset_orderset_union_schema(limit=1)

    await sync_to_async(TaskFactory.create)(name="AAA Other")
    await sync_to_async(TaskFactory.create)(name="BBB Task 1")
    await sync_to_async(ProjectFactory.create)(name="CCC Excluded")

    query = """
        query {
          searchables(filter: {nameContains: "1"}, orderBy: nameAsc) {
            __typename
            ... on TaskType { name }
            ... on ProjectType { name }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"searchables": [{"__typename": "TaskType", "name": "BBB Task 1"}]}


# Permissions


@pytest.mark.django_db
def test_union_type__entrypoint_permissions(graphql, undine_settings) -> None:
    """The entrypoint permission check runs for every instance from every member of the union."""
    seen: list[Any] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True)

        @searchables.permissions
        def searchables_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            seen.append(value)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    project = ProjectFactory.create(name="Project 1")

    response = graphql(SEARCHABLES_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "searchables": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
        ],
    }

    assert seen == [project, task]


@pytest.mark.django_db
def test_union_type__entrypoint_permissions__denied(graphql, undine_settings) -> None:
    """A denied entrypoint permission check surfaces as a GraphQL error."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True)

        @searchables.permissions
        def searchables_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql(SEARCHABLES_QUERY)

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
def test_union_type__query_type_permissions__denied(graphql, undine_settings) -> None:
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
        searchables = Entrypoint(Searchable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql(SEARCHABLES_QUERY)

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
async def test_union_type__entrypoint_permissions__sync_func__async(graphql_async, undine_settings) -> None:
    """A sync entrypoint permission check also runs on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True)

        @searchables.permissions
        def searchables_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(SEARCHABLES_QUERY)

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
async def test_union_type__entrypoint_permissions__async_func__async(graphql_async, undine_settings) -> None:
    """An async entrypoint permission check is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True)

        @searchables.permissions
        async def searchables_permissions(self, info: GQLInfo, value: Task | Project) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(SEARCHABLES_QUERY)

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
async def test_union_type__query_type_permissions__sync_func__async(graphql_async, undine_settings) -> None:
    """A sync query type permission check also runs on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchables = Entrypoint(Searchable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(SEARCHABLES_QUERY)

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
async def test_union_type__query_type_permissions__async_func__async(graphql_async, undine_settings) -> None:
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
        searchables = Entrypoint(Searchable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(SEARCHABLES_QUERY)

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
