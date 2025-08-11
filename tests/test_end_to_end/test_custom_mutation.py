from __future__ import annotations

import os
from typing import Any, TypedDict

import pytest
from asgiref.sync import sync_to_async
from graphql import GraphQLField, GraphQLList, GraphQLNonNull, GraphQLObjectType, GraphQLString

from example_project.app.models import Project, Task, TaskTypeChoices
from tests.factories import ProjectFactory, TaskFactory
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.converters import convert_to_graphql_type
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type
from undine.utils.model_utils import get_instance_or_raise


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")
def test_custom_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_custom_mutation__async(graphql_async, undine_settings):
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        @classmethod
        async def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            return await Task.objects.aget(pk=input_data["pk"])

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = await sync_to_async(TaskFactory.create)(name="Test task")

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

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "taskMutation": {
            "name": task.name,
        },
    }


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")
def test_custom_mutation__related(graphql, undine_settings):
    undine_settings.ASYNC = False

    related_input = None

    class TaskType(QueryType[Task]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        project = Input(RelatedProject)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal related_input
            related_input = input_data["project"]

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            instance.project = get_instance_or_raise(model=Project, pk=input_data["project"]["pk"])
            instance.save(update_fields=["project"])
            return instance

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task")
    project = ProjectFactory.create(name="Test project")

    data = {
        "pk": task.pk,
        "project": {
            "pk": project.pk,
        },
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

    task.refresh_from_db()
    assert task.project.name == "Test project"

    assert related_input == {"pk": project.pk}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_custom_mutation__related__async(graphql_async, undine_settings):
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        project = Input(RelatedProject)

        @classmethod
        async def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            instance.project = await Project.objects.aget(pk=input_data["project"]["pk"])
            await instance.asave(update_fields=["project"])
            return instance

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = await sync_to_async(TaskFactory.create)(name="Test task")
    project = await sync_to_async(ProjectFactory.create)(name="Test project")

    data = {
        "pk": task.pk,
        "project": {
            "pk": project.pk,
        },
    }
    query = """
        mutation($input: TaskMutation!) {
            taskMutation(input: $input) {
                name
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = await Task.objects.select_related("project").aget(pk=task.pk)
    assert task.project.name == "Test project"


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")
def test_custom_mutation__related_id(graphql, undine_settings):
    related_input = None

    class TaskType(QueryType[Task]): ...

    class TaskLinkProjectMutation(MutationType[Task]):
        pk = Input(required=True)
        project = Input(int, required=True)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal related_input
            related_input = input_data["project"]

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            instance.project = get_instance_or_raise(model=Project, pk=input_data["project"])
            instance.save(update_fields=["project"])
            return instance

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

    assert related_input == project.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_custom_mutation__related_id__async(graphql_async, undine_settings):
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    class TaskLinkProjectMutation(MutationType[Task]):
        pk = Input(required=True)
        project = Input(int, required=True)

        @classmethod
        async def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            instance.project = await Project.objects.aget(pk=input_data["project"])
            await instance.asave(update_fields=["project"])
            return instance

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        link_project = Entrypoint(TaskLinkProjectMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = await sync_to_async(TaskFactory.create)(name="Test task")
    project = await sync_to_async(ProjectFactory.create)(name="Test project")

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

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = await Task.objects.select_related("project").aget(pk=task.pk)
    assert task.project.name == "Test project"


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Does not work with async")  # TODO: Async
def test_custom_mutation__related_model(graphql, undine_settings):
    related_input = None

    class TaskType(QueryType[Task]): ...

    class TaskLinkProjectMutation(MutationType[Task]):
        pk = Input(required=True)
        project = Input(Project, required=True)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal related_input
            related_input = input_data["project"]

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            instance.project = input_data["project"]
            instance.save(update_fields=["project"])
            return instance

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

    assert related_input == project


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Does not work with async")  # TODO: Async
def test_custom_mutation__related_model__null(graphql, undine_settings):
    related_input = "foo"

    class TaskType(QueryType[Task]): ...

    class TaskLinkProjectMutation(MutationType[Task]):
        pk = Input(required=True)
        project = Input(Project, required=False)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal related_input
            related_input = input_data["project"]

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            instance.project = input_data["project"]
            instance.save(update_fields=["project"])
            return instance

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        link_project = Entrypoint(TaskLinkProjectMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task")

    data = {
        "pk": task.pk,
        "project": None,
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
    assert task.project is None

    assert related_input is None


@pytest.mark.django_db
def test_custom_mutation__custom_output_type(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        foo = Input(str, input_only=False, required=True)

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
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
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
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
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
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
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
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


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")
def test_custom_mutation__hidden_input(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        @Input(hidden=True, input_only=False)
        def name(self, info: GQLInfo) -> str:
            return "Modified"

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            instance.name = input_data["name"]
            instance.save(update_fields=["name"])
            return instance

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
            "name": "Modified",
        },
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_custom_mutation__hidden_input__async(graphql_async, undine_settings):
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        @Input(hidden=True, input_only=False)
        def name(self, info: GQLInfo) -> str:
            return "Modified"

        @classmethod
        async def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            instance.name = input_data["name"]
            await instance.asave(update_fields=["name"])
            return instance

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = await sync_to_async(TaskFactory.create)(name="Test task")

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

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "taskMutation": {
            "name": "Modified",
        },
    }


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")
def test_custom_mutation__input_only_input(graphql, undine_settings):
    input_only_data = None
    not_in_mutate = False

    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        foo = Input(str, input_only=True)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal input_only_data
            input_only_data = input_data["foo"]

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            nonlocal not_in_mutate
            not_in_mutate = "foo" not in input_data
            return instance

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task")

    data = {
        "pk": task.pk,
        "foo": "bar",
    }
    query = """
        mutation($input: TaskMutation!) {
            taskMutation(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "taskMutation": {
            "pk": task.pk,
        },
    }

    assert input_only_data == "bar"
    assert not_in_mutate is True


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_custom_mutation__input_only_input__async(graphql_async, undine_settings):
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    input_only_data = None
    not_in_mutate = False

    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        foo = Input(str, input_only=True)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal input_only_data
            input_only_data = input_data["foo"]

        @classmethod
        async def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
            nonlocal not_in_mutate
            not_in_mutate = "foo" not in input_data
            return instance

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        task_mutation = Entrypoint(TaskMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = await sync_to_async(TaskFactory.create)(name="Test task")

    data = {
        "pk": task.pk,
        "foo": "bar",
    }
    query = """
        mutation($input: TaskMutation!) {
            taskMutation(input: $input) {
                pk
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "taskMutation": {
            "pk": task.pk,
        },
    }

    assert input_only_data == "bar"
    assert not_in_mutate is True


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")
def test_custom_mutation__related_fake(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedTask(MutationType[Task], kind="related"):
        name = Input()
        type = Input()

    class ProjectCreateMutation(MutationType[Project]):
        name = Input()
        task_details = Input(RelatedTask, many=False, required=True)

        @classmethod
        def __mutate__(cls, instance: Project, info: GQLInfo, input_data: dict[str, Any]) -> Project:
            task_details = input_data.pop("task_details")

            for key, value in input_data.items():
                setattr(instance, key, value)
            instance.save()

            task = Task()
            task.project = instance
            for key, value in task_details.items():
                setattr(task, key, value)
            task.save()

            return instance

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_project = Entrypoint(ProjectCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Project",
        "taskDetails": {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK.value,
        },
    }
    query = """
        mutation($input: ProjectCreateMutation!) {
            createProject(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    project = Project.objects.get(pk=response.results["pk"])
    assert project.tasks.count() == 1
