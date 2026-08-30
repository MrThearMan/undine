from __future__ import annotations

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.relay import Connection, Node, to_global_id
from undine.utils.text import dotpath

NODE_QUERY = """
    query Node($id: ID!) {
      node(id: $id) {
        __typename
        id
        ... on TaskType {
          name
        }
      }
    }
"""

NODE_ID_QUERY = """
    query Node($id: ID!) {
      node(id: $id) {
        id
      }
    }
"""


@pytest.mark.django_db
def test_node__by_global_id(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    global_id = to_global_id(typename="TaskType", object_id=task.pk)

    response = graphql(NODE_QUERY, variables={"id": global_id})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "node": {
            "__typename": "TaskType",
            "id": global_id,
            "name": "Task 1",
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_node__by_global_id__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    global_id = to_global_id(typename="TaskType", object_id=task.pk)

    response = await graphql_async(NODE_QUERY, variables={"id": global_id})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "node": {
            "__typename": "TaskType",
            "id": global_id,
            "name": "Task 1",
        },
    }


@pytest.mark.django_db
def test_node__not_a_global_id(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(NODE_ID_QUERY, variables={"id": "foo"})

    assert response.errors == [
        {
            "message": "'foo' is not a valid Global ID.",
            "extensions": {
                "error_code": "NODE_INVALID_GLOBAL_ID",
                "status_code": 400,
            },
            "path": ["node"],
        },
    ]


@pytest.mark.django_db
def test_node__object_type_not_in_schema(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    global_id = to_global_id(typename="ProjectType", object_id=1)

    response = graphql(NODE_ID_QUERY, variables={"id": global_id})

    assert response.errors == [
        {
            "message": "Object type 'ProjectType' does not exist in schema.",
            "extensions": {
                "error_code": "NODE_MISSING_OBJECT_TYPE",
                "status_code": 400,
            },
            "path": ["node"],
        },
    ]


@pytest.mark.django_db
def test_node__object_does_not_exist(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    global_id = to_global_id(typename="TaskType", object_id=1)

    response = graphql(NODE_ID_QUERY, variables={"id": global_id})

    assert response.errors == [
        {
            "message": f"Primary key 1 on model '{dotpath(TaskType)}' did not match any row.",
            "extensions": {
                "error_code": "MODEL_INSTANCE_NOT_FOUND",
                "status_code": 404,
            },
            "path": ["node"],
        },
    ]


@pytest.mark.django_db
def test_node__type_not_object_type(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    global_id = to_global_id(typename="String", object_id=1)

    response = graphql(NODE_ID_QUERY, variables={"id": global_id})

    assert response.errors == [
        {
            "message": "Node ID type 'String' is not an object type.",
            "extensions": {
                "error_code": "NODE_TYPE_NOT_OBJECT_TYPE",
                "status_code": 400,
            },
            "path": ["node"],
        },
    ]


@pytest.mark.django_db
def test_node__missing_undine_query_type(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    global_id = to_global_id(typename="PageInfo", object_id=1)

    response = graphql(NODE_ID_QUERY, variables={"id": global_id})

    assert response.errors == [
        {
            "message": "Cannot find undine QueryType from object type 'PageInfo'.",
            "extensions": {
                "error_code": "NODE_QUERY_TYPE_MISSING",
                "status_code": 400,
            },
            "path": ["node"],
        },
    ]


@pytest.mark.django_db
def test_node__does_not_implement_node_interface(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    global_id = to_global_id(typename="TaskType", object_id=1)

    response = graphql(NODE_ID_QUERY, variables={"id": global_id})

    assert response.errors == [
        {
            "message": "Object type 'TaskType' must implement the 'Node' interface.",
            "extensions": {
                "error_code": "NODE_INTERFACE_MISSING",
                "status_code": 400,
            },
            "path": ["node"],
        },
    ]
