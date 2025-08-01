from __future__ import annotations

import os
from typing import Any, TypedDict

import pytest
from graphql import GraphQLField, GraphQLList, GraphQLNonNull, GraphQLObjectType, GraphQLString

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.converters import convert_to_graphql_type
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type
from undine.utils.model_utils import get_instance_or_raise


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")  # TODO: Async version
def test_custom_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        @classmethod
        def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            return get_instance_or_raise(model=Task, pk=input_data["pk"])

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task")

    data = {
        "pk": task.pk,
    }
    query = """
        mutation($input: TaskMutation!) {
            taskMutation(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "taskMutation": {
            "name": task.name,
        },
    }


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")  # TODO: Async version
def test_custom_mutation__related(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskLinkProjectMutation(MutationType[Task]):
        pk = Input(required=True)
        project = Input(Project, required=True)

        @classmethod
        def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            my_task = get_instance_or_raise(model=Task, pk=input_data["pk"])
            my_task.project = input_data["project"]
            my_task.save(update_fields=["project"])
            return my_task

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        link_project = Entrypoint(TaskLinkProjectMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task")
    project = ProjectFactory.create(name="Test project")

    data = {
        "pk": task.pk,
        "project": project.pk,
    }
    query = """
        mutation($input: TaskLinkProjectMutation!) {
            linkProject(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task.refresh_from_db()
    assert task.project == project


@pytest.mark.django_db
def test_custom_mutation__custom_output_type(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        foo = Input(str, input_only=False, required=True)

        @classmethod
        def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
            return {"bar": input_data["foo"]}

        @classmethod
        def __output_type__(cls) -> GraphQLObjectType:
            fields = {"bar": GraphQLField(GraphQLNonNull(GraphQLString))}
            return get_or_create_graphql_object_type(name="TaskMutationOutput", fields=fields)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "foo": "123",
    }
    query = """
        mutation($input: TaskMutation!) {
            taskMutation(input: $input) {
                bar
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "taskMutation": {
            "bar": "123",
        },
    }


@pytest.mark.django_db
def test_custom_mutation__default_of_list(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        foo = Input(list[str], input_only=False, default_value=["123"])

        @classmethod
        def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
            # Try to modify the default value. Should not persist between mutations.
            input_data["foo"].append("456")
            return {"bar": input_data["foo"]}

        @classmethod
        def __output_type__(cls) -> GraphQLObjectType:
            fields = {"bar": GraphQLField(GraphQLList(GraphQLString))}
            return get_or_create_graphql_object_type(name="TaskMutationOutput", fields=fields)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    assert TaskMutation.foo.as_graphql_input_field()

    data = {}
    query = """
        mutation($input: TaskMutation!) {
            taskMutation(input: $input) {
                bar
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors
    assert response.data == {"taskMutation": {"bar": ["123", "456"]}}

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors
    assert response.data == {"taskMutation": {"bar": ["123", "456"]}}


@pytest.mark.django_db
def test_custom_mutation__default_of_list__no_variable(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        foo = Input(list[str], input_only=False, default_value=["123"])

        @classmethod
        def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
            # Try to modify the default value. Should not persist between mutations.
            input_data["foo"].append("456")
            return {"bar": input_data["foo"]}

        @classmethod
        def __output_type__(cls) -> GraphQLObjectType:
            fields = {"bar": GraphQLField(GraphQLList(GraphQLString))}
            return get_or_create_graphql_object_type(name="TaskMutationOutput", fields=fields)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    assert TaskMutation.foo.as_graphql_input_field()

    query = """
        mutation {
            taskMutation(input: {}) {
                bar
            }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {"taskMutation": {"bar": ["123", "456"]}}

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {"taskMutation": {"bar": ["123", "456"]}}


class FooInput(TypedDict):
    fizz: str
    buzz: int


@pytest.mark.django_db
def test_custom_mutation__default_of_dict(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        foo = Input(FooInput, input_only=False, default_value=FooInput(fizz="123", buzz=1))

        @classmethod
        def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
            # Try to modify the default value. Should not persist between mutations.
            input_data["foo"]["buzz"] = 2
            return {"bar": input_data["foo"]}

        @classmethod
        def __output_type__(cls) -> GraphQLObjectType:
            fields = {"bar": GraphQLField(convert_to_graphql_type(FooInput))}
            return get_or_create_graphql_object_type(name="TaskMutationOutput", fields=fields)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    assert TaskMutation.foo.as_graphql_input_field()

    data = {}
    query = """
        mutation($input: TaskMutation!) {
            taskMutation(input: $input) {
                bar {
                    fizz
                    buzz
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors
    assert response.data == {"taskMutation": {"bar": {"fizz": "123", "buzz": 2}}}

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors
    assert response.data == {"taskMutation": {"bar": {"fizz": "123", "buzz": 2}}}
