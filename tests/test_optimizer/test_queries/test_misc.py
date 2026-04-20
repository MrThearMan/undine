from __future__ import annotations

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Value

from example_project.app.models import Person, Project, Task, Team
from tests.conftest import skip_if_async
from tests.factories import PersonFactory, ProjectFactory, TaskFactory, TeamFactory
from undine import Entrypoint, Field, Filter, FilterSet, GQLInfo, Order, OrderSet, QueryType, RootType, create_schema
from undine.exceptions import EmptyFilterResult
from undine.optimizer import optimize_async, optimize_sync
from undine.typing import DjangoExpression


@pytest.mark.django_db
def test_optimizer__multiple_queries(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create(name="foo")
    TaskFactory.create(name="foo", project=project)

    query = """
        query {
          tasks {
            name
          }
          projects {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "foo"}], "projects": [{"name": "foo"}]}


@pytest.mark.django_db
@skip_if_async
def test_optimizer__optimize_sync__with_limit(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

        @tasks.resolve
        def resolve_tasks(self, info: GQLInfo) -> list[Task]:
            qs = Task.objects.all()
            return optimize_sync(qs, info, limit=2)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="T1")
    TaskFactory.create(name="T2")
    TaskFactory.create(name="T3")

    response = graphql("query { tasks { name } }")
    assert response.has_errors is False, response.errors
    assert len(response.data["tasks"]) == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_optimizer__optimize_async__with_kwargs(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.resolve
        async def resolve_task(self, info: GQLInfo, *, pk: int) -> Task | None:
            qs = Task.objects.all()
            return await optimize_async(qs, info, pk=pk)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="single")

    response = await graphql_async(f"query {{ task(pk: {task.pk}) {{ name }} }}")
    assert response.has_errors is False, response.errors
    assert response.data == {"task": {"name": "single"}}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_optimizer__optimize_async__with_limit(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

        @tasks.resolve
        async def resolve_tasks(self, info: GQLInfo) -> list[Task]:
            qs = Task.objects.all()
            return await optimize_async(qs, info, limit=2)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="A")
    await sync_to_async(TaskFactory.create)(name="B")
    await sync_to_async(TaskFactory.create)(name="C")

    response = await graphql_async("query { tasks { name } }")
    assert response.has_errors is False, response.errors
    assert len(response.data["tasks"]) == 2


@pytest.mark.django_db
def test_optimizer__handle_undine_field__no_undine_field(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        done = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo", done=True)

    response = graphql("query { tasks { name done } }")
    assert response.has_errors is False, response.errors
    assert response.data == {"tasks": [{"name": "foo", "done": True}]}


@pytest.mark.django_db
def test_optimizer__extend__prefetch_in_select_related(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TeamType(QueryType[Team], auto=False):
        name = Field()
        members = Field(PersonType)

    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        team = Field(TeamType)

    class TaskType2(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType2, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person = PersonFactory.create(name="Alice")
    team = TeamFactory.create(name="T1", members=[person])
    project = ProjectFactory.create(name="P1", team=team)
    TaskFactory.create(name="Task1", project=project)

    query = """
        query {
          tasks {
            name
            project {
              name
              team {
                name
                members {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors
    assert response.data["tasks"][0]["project"]["team"]["members"] == [{"name": "Alice"}]


@pytest.mark.django_db
def test_optimizer__apply__select_related_and_only(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create(name="P")
    TaskFactory.create(name="T", project=project)

    response = graphql("query { tasks { name project { name } } }", count_queries=True)
    assert response.has_errors is False, response.errors
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__apply__none_queryset(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        @Filter
        def none_filter(self, info: GQLInfo, *, value: bool) -> None:  # type: ignore[return]
            raise EmptyFilterResult

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="should-not-appear")

    query = """
        query {
          tasks(filter: { noneFilter: true }) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert response.data == {"tasks": []}


@pytest.mark.django_db
def test_optimizer__apply__with_aliases(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

        @name.aliases
        def name_aliases(self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]:
            return {"name_alias": Value("alias_value")}

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="alpha")
    TaskFactory.create(name="beta")

    query = """
        query {
          tasks(orderBy: [nameAsc]) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert len(response.data["tasks"]) == 2


@pytest.mark.django_db
def test_optimizer__apply__with_distinct(graphql, undine_settings) -> None:

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter(distinct=True)

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="T1")
    TaskFactory.create(name="T2")

    query = """
        query {
          tasks(filter: { name: "T1" }) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert response.data == {"tasks": [{"name": "T1"}]}


@pytest.mark.django_db
def test_optimizer__max_query_complexity(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 5

    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        tasks = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create(name="foo")
    TaskFactory.create(name="bar", project=project)
    TaskFactory.create(name="baz", project=project)
    TaskFactory.create(name="buzz", project=project)

    query = """
        query {
          tasks {
            project {
              tasks {
                project {
                  tasks {
                    project {
                      tasks {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.error_message(0) == "Query complexity of 6 exceeds the maximum allowed complexity of 5."


@pytest.mark.django_db
def test_optimizer__too_many_filters(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()
        type = Filter()

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)
    undine_settings.MAX_FILTERS_PER_TYPE = 1

    query = """
        query {
          tasks(filter: { name: "foo", type: STORY }) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is True
    assert any("TOO_MANY_FILTERS" in str(e) or "too many" in str(e).lower() for e in response.errors)


@pytest.mark.django_db
def test_optimizer__too_many_orders(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()
        type = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)
    undine_settings.MAX_ORDERS_PER_TYPE = 1

    query = """
        query {
          tasks(orderBy: [nameAsc, typeAsc]) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is True
    assert any("TOO_MANY_ORDERS" in str(e) or "too many" in str(e).lower() for e in response.errors)
