from __future__ import annotations

from typing import TypedDict

import pytest
from asgiref.sync import sync_to_async
from django.db.models import QuerySet, Value
from graphql import FieldNode, GraphQLNonNull, GraphQLString, NameNode, SelectionSetNode

from example_project.app.models import Comment, Person, Project, Task, TaskTypeChoices, Team
from example_project.example.models import Example, ExampleGeneric, ExampleROTO
from tests.factories import CommentFactory, ExampleFactory, PersonFactory, ProjectFactory, TaskFactory, TeamFactory
from tests.helpers import mock_gql_info
from undine import (
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    Input,
    InterfaceField,
    InterfaceType,
    MutationType,
    Order,
    OrderSet,
    QueryType,
    RootType,
    create_schema,
)
from undine.exceptions import EmptyFilterResult
from undine.optimizer.ast_walker import GraphQLASTWalker
from undine.optimizer.optimizer import OptimizationData, QueryOptimizer, optimize_async, optimize_sync
from undine.relay import Connection
from undine.settings import example_schema
from undine.typing import DjangoExpression


def test_optimizer__ast_walker__handle_query_class__no_selection_set() -> None:
    # Use the example schema's "testing" scalar field — selection_set will be None
    field_node = FieldNode(
        loc=None,
        directives=(),
        alias=None,
        name=NameNode(value="testing"),
        arguments=(),
        selection_set=None,
    )

    parent_type = example_schema.query_type
    info = mock_gql_info(field_nodes=[field_node], parent_type=parent_type, schema=example_schema)

    walker = GraphQLASTWalker(info=info, model=Task)
    # selection_set is None → should return without walking any selections
    walker.handle_query_class(parent_type, field_node)


@pytest.mark.django_db
def test_optimizer__abstract_type__skip_inline_fragment(graphql, undine_settings) -> None:

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)
        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)

    query = """
        query {
          named {
            name
            ... on ProjectType @skip(if: true) {
              pk
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # ProjectType fragment was skipped, so only TaskType fields appear
    assert all("pk" not in item for item in response.data["named"])


@pytest.mark.django_db
def test_optimizer__abstract_type__inline_fragment_no_type_condition(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)
        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="P1")
    TaskFactory.create(name="T1", type=TaskTypeChoices.BUG_FIX)

    # Fragment spread that gets expanded by flatten_abstract_type_selections
    # This exercises the type_condition is None branch for inline fragments
    # on an abstract type when no type condition is specified
    query = """
        query {
          named {
            ... {
              name
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    named = response.data["named"]
    assert len(named) > 0


@pytest.mark.django_db
def test_optimizer__interface_only_fields__no_undine_interface(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)
        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.STORY)

    # Only interface fields — no fragments — exercises the
    # "types_without_fragments" loop with undine_interface check
    query = """
        query {
          named {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert len(response.data["named"]) == 2


@pytest.mark.django_db
def test_optimizer__connection__scalar_field_no_selection_set(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    # pageInfo.hasNextPage is a scalar within connection — exercises 198->exit
    query = """
        query {
          tasks {
            pageInfo {
              hasNextPage
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert "hasNextPage" in response.data["tasks"]["pageInfo"]


@pytest.mark.django_db
def test_optimizer__generic_foreign_key__with_selection_set(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    project = ProjectFactory.create(name="my-project")
    CommentFactory.create(contents="c1", target=task)
    CommentFactory.create(contents="c2", target=project)

    query = """
        query {
          comments {
            target {
              ... on TaskType {
                type
              }
              ... on ProjectType {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "comments": [
            {"target": {"type": "STORY"}},
            {"target": {"name": "my-project"}},
        ],
    }


@pytest.mark.django_db
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
def test_optimizer__mutation__filter_queryset(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()

        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
            return queryset

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="original")

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
          }
        }
    """

    response = graphql(query, variables={"input": {"pk": task.pk, "name": "updated"}})
    assert response.has_errors is False, response.errors
    assert response.data == {"updateTask": {"name": "updated"}}


@pytest.mark.django_db
def test_optimizer__mutation__no_input_arg(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        @Entrypoint
        def delete_task(self, info: GQLInfo, *, pk: int) -> bool:
            Task.objects.filter(pk=pk).delete()
            return True

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="to-delete")

    response = graphql(f"mutation {{ deleteTask(pk: {task.pk}) }}")
    assert response.has_errors is False, response.errors
    assert response.data == {"deleteTask": True}


@pytest.mark.django_db
def test_optimizer__mutation_type__no_input_arg_with_query_type(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    # Putting a QueryType entrypoint on the Mutation type causes optimizer to run
    # with parent_type = mutation_type, but field has no 'input' arg → 209->215.
    class Mutation(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="test-task")

    response = graphql(f"mutation {{ task(pk: {task.pk}) {{ name }} }}")
    assert response.has_errors is False, response.errors
    assert response.data == {"task": {"name": "test-task"}}


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
def test_optimizer__total_count__no_pagination(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="T1")
    TaskFactory.create(name="T2")

    # totalCount in a connection without cursor pagination → pagination is None
    query = """
        query {
          tasks {
            totalCount
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert response.data["tasks"]["totalCount"] == 2


@pytest.mark.django_db
def test_optimizer__to_one_field__reverse_one_to_one(graphql, undine_settings) -> None:
    class ExampleROTOType(QueryType[ExampleROTO], auto=False):
        name = Field()

    class ExampleType(QueryType[Example], auto=False):
        name = Field()
        example_roto = Field(ExampleROTOType)

    class Query(RootType):
        examples = Entrypoint(ExampleType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ExampleFactory.create(name="E1", example_roto__name="R1")
    ExampleFactory.create(name="E2", example_roto__name="R2")

    query = """
        query {
          examples {
            name
            exampleRoto {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    results = response.data["examples"]
    assert any(r["exampleRoto"]["name"] == "R1" for r in results)


@pytest.mark.django_db
def test_optimizer__to_many_field__generic_relation(graphql, undine_settings) -> None:
    class ExampleGenericType(QueryType[ExampleGeneric], auto=False):
        name = Field()

    class ExampleType(QueryType[Example], auto=False):
        name = Field()
        generic = Field(ExampleGenericType)

    class Query(RootType):
        examples = Entrypoint(ExampleType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ExampleFactory.create(name="Ex1", generic__name="g1")
    ExampleFactory.create(name="Ex2", generic__name="g2")

    query = """
        query {
          examples {
            name
            generic {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors
    assert len(response.data["examples"]) == 2


@pytest.mark.django_db
def test_optimizer__to_many_field__with_alias(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person = PersonFactory.create(name="Alice")
    TaskFactory.create(name="T1", assignees=[person])

    # Using a GraphQL alias on a many field triggers alias handling
    query = """
        query {
          tasks {
            name
            people: assignees {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert response.data["tasks"][0]["people"] == [{"name": "Alice"}]


@pytest.mark.django_db
def test_optimizer__generic_prefetch__reuse_existing(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.BUG_FIX.value)
    CommentFactory.create(contents="c1", target=task)
    CommentFactory.create(contents="c2", target=task)

    query = """
        query {
          comments {
            target {
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert all(c["target"]["type"] == "BUG_FIX" for c in response.data["comments"])


@pytest.mark.django_db
def test_optimizer__add_select_related__with_query_type(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_select_related("project", query_type=ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Proj")
    TaskFactory.create(name="T1", project=Project.objects.first())

    response = graphql("query { tasks { name } }", count_queries=True)
    assert response.has_errors is False, response.errors
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__add_prefetch_related__with_query_type(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_prefetch_related("assignees", query_type=PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person = PersonFactory.create(name="Bob")
    TaskFactory.create(name="T1", assignees=[person])

    response = graphql("query { tasks { name } }", count_queries=True)
    assert response.has_errors is False, response.errors
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__add_generic_prefetch_related__with_query_type(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_generic_prefetch_related("target", Task, query_type=TaskType)

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    CommentFactory.create(contents="c", target=task)

    response = graphql("query { comments { target { ... on TaskType { type } } } }")
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_optimizer__fill_from_mutation_type__custom_filter(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()

        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
            return queryset.filter(done=False)

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="active", done=False)

    response = graphql(
        "mutation ($input: TaskUpdateMutation!) { updateTask(input: $input) { name } }",
        variables={"input": {"pk": task.pk, "name": "renamed"}},
    )
    assert response.has_errors is False, response.errors
    assert response.data == {"updateTask": {"name": "renamed"}}


@pytest.mark.django_db
def test_optimizer__process__generic_prefetch_to_attr(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.TASK.value)
    project = ProjectFactory.create(name="P1")
    CommentFactory.create(contents="a", target=task)
    CommentFactory.create(contents="b", target=project)

    query = """
        query {
          comments {
            target {
              ... on TaskType { type }
              ... on ProjectType { name }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors
    assert len(response.data["comments"]) == 2


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


# ---- ast_walker.py coverage gaps ----


def test_ast_walker__handle_connection__selection_set_none() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    schema = create_schema(query=Query)
    connection_type = schema.type_map["TaskTypeConnection"]

    field_node = FieldNode(
        loc=None,
        directives=(),
        alias=None,
        name=NameNode(value="edges"),
        arguments=(),
        selection_set=None,
    )

    info = mock_gql_info(schema=schema, parent_type=connection_type)
    walker = GraphQLASTWalker(info=info, model=Task)
    walker.handle_connection(connection_type, field_node)


def test_ast_walker__handle_generic_foreign_key__base_class() -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    schema = create_schema(query=Query)
    comment_type = schema.type_map["CommentType"]

    field_node = FieldNode(
        loc=None,
        directives=(),
        alias=None,
        name=NameNode(value="target"),
        arguments=(),
        selection_set=SelectionSetNode(selections=()),
    )

    info = mock_gql_info(schema=schema, parent_type=comment_type)
    walker = GraphQLASTWalker(info=info, model=Comment)
    target_field = Comment._meta.get_field("target")
    walker.handle_generic_foreign_key(comment_type, field_node, target_field)


def test_ast_walker__get_model__no_query_type() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)

    from graphql import GraphQLObjectType  # noqa: PLC0415

    plain_type = GraphQLObjectType("PlainType", fields={"id": lambda: {}})

    info = mock_gql_info(schema=schema)
    walker = GraphQLASTWalker(info=info, model=Task)
    result = walker.get_model(plain_type)
    assert result is None


@pytest.mark.django_db
def test_ast_walker__flatten_abstract_type_selections__fragment_spread(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)
        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="T1", type=TaskTypeChoices.TASK)
    ProjectFactory.create(name="P1")

    query = """
        query {
          named {
            ...NamedFragment
          }
        }

        fragment NamedFragment on Named {
          ... on TaskType {
            type
          }
          ... on ProjectType {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert len(response.data["named"]) == 2


# ---- optimizer.py coverage gaps ----


@pytest.mark.django_db
def test_optimizer__mutation__input_not_mutation_type(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskInput(TypedDict):
        name: str

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        @Entrypoint
        def create_task(self, info: GQLInfo, *, input: TaskInput) -> int:  # noqa: A002
            task = TaskFactory.create(
                name=input["name"],
                type=TaskTypeChoices.TASK.value,
            )
            return task.pk

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    response = graphql('mutation { createTask(input: { name: "New Task" }) }')
    assert response.has_errors is False, response.errors
    assert response.data["createTask"] is not None


def test_optimizer__handle_total_count__pagination_none() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    info = mock_gql_info(schema=schema)
    optimizer = QueryOptimizer(model=Task, info=info)

    assert optimizer.optimization_data.pagination is None

    field_node = FieldNode(
        loc=None,
        directives=(),
        alias=None,
        name=NameNode(value="totalCount"),
        arguments=(),
        selection_set=None,
    )

    from graphql import GraphQLScalarType  # noqa: PLC0415

    scalar = GraphQLScalarType("TotalCountScalar")
    optimizer.handle_total_count(scalar, field_node)


@pytest.mark.django_db
def test_optimizer__generic_foreign_key__skip_inline_fragment(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    CommentFactory.create(contents="c1", target=task)

    query = """
        query {
          comments {
            target {
              ... on TaskType @skip(if: true) {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_optimizer__generic_foreign_key__typename_field(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.TASK.value)
    CommentFactory.create(contents="c1", target=task)

    query = """
        query {
          comments {
            target {
              __typename
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_optimizer__generic_foreign_key__inline_fragment_no_type_condition(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.BUG_FIX.value)
    CommentFactory.create(contents="test", target=task)

    query = """
        query {
          comments {
            target {
              ... {
                __typename
              }
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_optimizer__generic_prefetch__custom_to_attr(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_generic_prefetch_related("target", Task, query_type=TaskType, to_attr="task_target")
            data.add_generic_prefetch_related("target", Project, query_type=ProjectType, to_attr="task_target")

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    CommentFactory.create(contents="c1", target=task)

    response = graphql("query { comments { target { ... on TaskType { type } } } }")
    assert response.has_errors is False, response.errors


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
    from django.db.models import Q  # noqa: PLC0415

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
