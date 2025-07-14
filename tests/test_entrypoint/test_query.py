from __future__ import annotations

from inspect import cleandoc

import pytest
from graphql import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
)

from example_project.app.models import Task
from undine import Entrypoint, FilterSet, GQLInfo, OrderSet, QueryType, RootType
from undine.exceptions import MissingEntrypointRefError
from undine.optimizer.optimizer import optimize_sync
from undine.resolvers import EntrypointFunctionResolver, QueryTypeManyResolver, QueryTypeSingleResolver


def test_entrypoint__missing_reference() -> None:
    with pytest.raises(MissingEntrypointRefError):

        class Query(RootType):
            foo = Entrypoint()


def test_entrypoint__description_in_entrypoint() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        foo = Entrypoint(TaskType, description="Actual description.")

    assert Query.foo.description == "Actual description."


def test_entrypoint__deprecation_reason() -> None:
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        foo = Entrypoint(TaskType, deprecation_reason="Use something else.")

    assert Query.foo.deprecation_reason == "Use something else."


def test_entrypoint__query__repr() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType)

    assert repr(Query.task) == f"<undine.entrypoint.Entrypoint(ref={TaskType!r})>"


def test_entrypoint__query__str() -> None:
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    assert str(Query.task) == cleandoc(
        """
        task(
          pk: Int!
        ): TaskType!
        """
    )


def test_entrypoint__query__attributes() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType)

    assert Query.task.ref == TaskType
    assert Query.task.many is False
    assert Query.task.description == "Description."
    assert Query.task.deprecation_reason is None
    assert Query.task.extensions == {"undine_entrypoint": Query.task}
    assert Query.task.root_type == Query
    assert Query.task.name == "task"


def test_entrypoint__query__get_field_type() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType)

    field_type = Query.task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLObjectType)


def test_entrypoint__query__get_field_arguments() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType)

    arguments = Query.task.get_field_arguments()

    assert arguments == {"pk": GraphQLArgument(GraphQLNonNull(GraphQLInt), out_name="pk")}


def test_entrypoint__query__get_resolver() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver = Query.task.get_resolver()
    assert isinstance(resolver, QueryTypeSingleResolver)


def test_entrypoint__query__as_graphql_field() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType)

    graphql_field = Query.task.as_graphql_field()

    assert isinstance(graphql_field.type, GraphQLNonNull)
    assert isinstance(graphql_field.type.of_type, GraphQLObjectType)

    assert graphql_field.args == {"pk": GraphQLArgument(GraphQLNonNull(GraphQLInt), out_name="pk")}
    assert isinstance(graphql_field.resolve, QueryTypeSingleResolver)
    assert graphql_field.description == "Description."
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_entrypoint": Query.task}


def test_entrypoint__query__many__attributes() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType, many=True)

    assert Query.task.ref == TaskType
    assert Query.task.many is True
    assert Query.task.description == "Description."
    assert Query.task.deprecation_reason is None
    assert Query.task.extensions == {"undine_entrypoint": Query.task}
    assert Query.task.root_type == Query
    assert Query.task.name == "task"


def test_entrypoint__query__many__get_field_type() -> None:
    class TaskType(QueryType[Task]):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType, many=True)

    field_type = Query.task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLList)
    assert isinstance(field_type.of_type.of_type, GraphQLNonNull)
    assert isinstance(field_type.of_type.of_type.of_type, GraphQLObjectType)


def test_entrypoint__query__many__get_field_arguments() -> None:
    class TaskFilterSet(FilterSet[Task]): ...

    class TaskOrderSet(OrderSet[Task]): ...

    class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet):
        """Description."""

    class Query(RootType):
        task = Entrypoint(TaskType, many=True)

    arguments = Query.task.get_field_arguments()
    assert sorted(arguments) == ["filter", "orderBy"]

    assert isinstance(arguments["filter"], GraphQLArgument)
    assert isinstance(arguments["filter"].type, GraphQLInputObjectType)

    assert isinstance(arguments["orderBy"], GraphQLArgument)
    assert isinstance(arguments["orderBy"].type, GraphQLList)
    assert isinstance(arguments["orderBy"].type.of_type, GraphQLNonNull)
    assert isinstance(arguments["orderBy"].type.of_type.of_type, GraphQLEnumType)


def test_entrypoint__query__many__get_resolver() -> None:
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, many=True)

    resolver = Query.task.get_resolver()
    assert isinstance(resolver, QueryTypeManyResolver)


def test_entrypoint__query__custom_resolver() -> None:
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.resolve
        def resolve_task(self, info: GQLInfo, name: str) -> list[Task]:
            qs = Task.objects.filter(name__icontains=name)
            return optimize_sync(qs, info)

    resolver = Query.task.get_resolver()
    assert isinstance(resolver, EntrypointFunctionResolver)

    args = Query.task.get_field_arguments()
    assert args == {"name": GraphQLArgument(GraphQLNonNull(GraphQLString), out_name="name")}
