from __future__ import annotations

from inspect import isawaitable
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from graphql import GraphQLEnumType, GraphQLEnumValue, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.exceptions import (
    GraphQLNodeIDFieldTypeError,
    GraphQLNodeInterfaceMissingError,
    GraphQLNodeInvalidGlobalIDError,
    GraphQLNodeMissingIDFieldError,
    GraphQLNodeObjectTypeMissingError,
    GraphQLNodeQueryTypeMissingError,
    GraphQLNodeTypeNotObjectTypeError,
)
from undine.relay import Node, to_global_id
from undine.resolvers import NodeResolver


@pytest.mark.django_db
def test_resolvers__node_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer():
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db(transaction=True)
async def test_resolvers__node_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer():
        coroutine = resolver(root=task, info=info, id=object_id)
        assert isawaitable(coroutine)

        result = await coroutine
        assert result == task


@pytest.mark.django_db
def test_resolvers__node_resolver__not_a_global_id(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)

    with patch_optimizer(), pytest.raises(GraphQLNodeInvalidGlobalIDError):
        assert resolver(root=task, info=info, id="foo") == task


@pytest.mark.django_db
def test_resolvers__node_resolver__object_type_not_in_schema(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename="ProjectType", object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeObjectTypeMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__does_not_implement_node_interface(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeInterfaceMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__missing_undine_query_type(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    TaskType.__extensions__ = {}  # Remove undine QueryType extension on purpose.

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeQueryTypeMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__missing_id_field(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskType.__field_map__.pop("id")  # Remove `id` field on purpose

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeMissingIDFieldError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__type_not_object_type(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename="SomeEnum", object_id=task.pk)

    # Patch schema.get_type to return an Enum (not a GraphQLObjectType)
    enum_type = GraphQLEnumType("SomeEnum", {"A": GraphQLEnumValue("A")})
    with (
        patch.object(undine_settings.SCHEMA, "get_type", return_value=enum_type),
        pytest.raises(GraphQLNodeTypeNotObjectTypeError),
    ):
        resolver(root=task, info=info, id=object_id)


@pytest.mark.django_db
def test_resolvers__node_resolver__id_field_wrong_type(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    # Make the id field have a non-ID type by patching get_field_type
    id_field = TaskType.__field_map__["id"]
    with (
        patch.object(id_field, "get_field_type", return_value=GraphQLNonNull(GraphQLString)),
        pytest.raises(GraphQLNodeIDFieldTypeError),
    ):
        resolver(root=task, info=info, id=object_id)
