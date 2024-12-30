import pytest
from django.db.models import Prefetch, QuerySet, Value
from graphql import FieldNode, NameNode

from example_project.app.models import Person, Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo, patch_optimizer
from undine import Entrypoint, Field, QueryType, create_schema
from undine.errors.exceptions import (
    GraphQLNodeIDFieldTypeError,
    GraphQLNodeInterfaceMissingError,
    GraphQLNodeInvalidGlobalIDError,
    GraphQLNodeMissingIDFieldError,
    GraphQLNodeObjectTypeMissingError,
    GraphQLNodeQueryTypeMissingError,
)
from undine.relay import Connection, Node, offset_to_cursor, to_global_id
from undine.resolvers import ConnectionResolver, GlobalIDResolver, NestedConnectionResolver, NodeResolver
from undine.typing import ConnectionDict, NodeDict, PageInfoDict


@pytest.mark.django_db
def test_resolvers__global_id_resolver():
    class TaskType(QueryType, model=Task): ...

    task = TaskFactory.create()

    resolver = GlobalIDResolver(typename=TaskType.__typename__)

    object_id = to_global_id(typename=TaskType.__typename__, object_id=task.pk)

    assert resolver(root=task, info=MockGQLInfo()) == object_id


@pytest.mark.django_db
def test_resolvers__node_resolver(undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]): ...

    class Query:
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create()

    resolver = NodeResolver()
    info = MockGQLInfo(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__typename__, object_id=task.pk)

    with patch_optimizer():
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__not_a_global_id(undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]): ...

    class Query:
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create()

    resolver = NodeResolver()
    info = MockGQLInfo(schema=undine_settings.SCHEMA)

    with patch_optimizer(), pytest.raises(GraphQLNodeInvalidGlobalIDError):
        assert resolver(root=task, info=info, id="foo") == task


@pytest.mark.django_db
def test_resolvers__node_resolver__object_type_not_in_schema(undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]): ...

    class Query:
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create()

    resolver = NodeResolver()
    info = MockGQLInfo(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename="ProjectType", object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeObjectTypeMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__does_not_implement_node_interface(undine_settings):
    class TaskType(QueryType, model=Task, auto=False): ...

    class Query:
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create()

    resolver = NodeResolver()
    info = MockGQLInfo(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__typename__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeInterfaceMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__missing_undine_query_type(undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]): ...

    TaskType.__extensions__ = {}  # Remove undine QueryType extension on purpose.

    class Query:
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create()

    resolver = NodeResolver()
    info = MockGQLInfo(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__typename__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeQueryTypeMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__missing_id_field(undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]): ...

    TaskType.__field_map__.pop("id")  # Remove `id` field on purpose

    class Query:
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create()

    resolver = NodeResolver()
    info = MockGQLInfo(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__typename__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeMissingIDFieldError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__id_not_global_id(undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        id = Field()

    class Query:
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create()

    resolver = NodeResolver()
    info = MockGQLInfo(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__typename__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeIDFieldTypeError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__connection_resolver(undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]): ...

    task = TaskFactory.create()

    resolver = ConnectionResolver(connection=Connection(TaskType))

    def optimize(qs: QuerySet) -> QuerySet:
        qs._hints[undine_settings.CONNECTION_TOTAL_COUNT_KEY] = 100
        qs._hints[undine_settings.CONNECTION_START_INDEX_KEY] = 0
        qs._hints[undine_settings.CONNECTION_STOP_INDEX_KEY] = 1
        return qs

    with patch_optimizer(func=optimize):
        result = resolver(root=task, info=MockGQLInfo())

    typename = TaskType.__typename__
    assert result == (
        ConnectionDict(
            totalCount=100,
            pageInfo=PageInfoDict(
                hasNextPage=True,
                hasPreviousPage=False,
                startCursor=offset_to_cursor(typename, 0),
                endCursor=offset_to_cursor(typename, 0),
            ),
            edges=[
                NodeDict(
                    cursor=offset_to_cursor(typename, 0),
                    node=task,
                ),
            ],
        )
    )


@pytest.mark.django_db
def test_resolvers__nested_connection_resolver(undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]): ...

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        assignees = Field(Connection(PersonType))

    TaskFactory.create(assignees__name="Test assignee")

    task = Task.objects.prefetch_related(
        Prefetch(
            "assignees",
            queryset=Person.objects.annotate(
                **{
                    undine_settings.CONNECTION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.CONNECTION_START_INDEX_KEY: Value(0),
                    undine_settings.CONNECTION_STOP_INDEX_KEY: Value(1),
                },
            ),
        ),
    ).first()

    assignee = task.assignees.first()

    resolver = NestedConnectionResolver(connection=TaskType.assignees.ref, field=TaskType.assignees)

    result = resolver(root=task, info=MockGQLInfo())

    typename = PersonType.__typename__
    assert result == (
        ConnectionDict(
            totalCount=100,
            pageInfo=PageInfoDict(
                hasNextPage=True,
                hasPreviousPage=False,
                startCursor=offset_to_cursor(typename, 0),
                endCursor=offset_to_cursor(typename, 0),
            ),
            edges=[
                NodeDict(
                    cursor=offset_to_cursor(typename, 0),
                    node=assignee,
                ),
            ],
        )
    )


@pytest.mark.django_db
def test_resolvers__nested_connection_resolver__to_attr(undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]): ...

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        assignees = Field(Connection(PersonType))

    TaskFactory.create(assignees__name="Test assignee")

    task = Task.objects.prefetch_related(
        Prefetch(
            "assignees",
            queryset=Person.objects.annotate(
                **{
                    undine_settings.CONNECTION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.CONNECTION_START_INDEX_KEY: Value(0),
                    undine_settings.CONNECTION_STOP_INDEX_KEY: Value(1),
                },
            ),
            to_attr="original_assignees",
        ),
    ).first()

    assignee = task.original_assignees[0]

    resolver = NestedConnectionResolver(connection=TaskType.assignees.ref, field=TaskType.assignees)

    field_nodes = [
        FieldNode(
            loc=None,
            directives=(),
            alias=NameNode(value="original_assignees"),
            name=NameNode(value="assignees"),
            arguments=(),
            selection_set=None,
        ),
    ]

    result = resolver(root=task, info=MockGQLInfo(field_nodes=field_nodes))

    typename = PersonType.__typename__
    assert result == (
        ConnectionDict(
            totalCount=100,
            pageInfo=PageInfoDict(
                hasNextPage=True,
                hasPreviousPage=False,
                startCursor=offset_to_cursor(typename, 0),
                endCursor=offset_to_cursor(typename, 0),
            ),
            edges=[
                NodeDict(
                    cursor=offset_to_cursor(typename, 0),
                    node=assignee,
                ),
            ],
        )
    )
