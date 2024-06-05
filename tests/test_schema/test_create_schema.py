from __future__ import annotations

import pytest
from graphql import GraphQLObjectType

from example_project.app.models import Task
from undine import Entrypoint, Field, MutationType, QueryType, RootType, create_schema
from undine.utils.graphql.type_registry import GRAPHQL_REGISTRY


def test_create_schema() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=Mutation)

    assert isinstance(schema.query_type, GraphQLObjectType)
    assert schema.query_type.name == "Query"
    assert sorted(schema.query_type.fields) == ["task"]

    assert isinstance(schema.mutation_type, GraphQLObjectType)
    assert schema.mutation_type.name == "Mutation"
    assert sorted(schema.mutation_type.fields) == ["createTask"]


def test_create_schema__registered() -> None:
    assert "Query" not in GRAPHQL_REGISTRY
    assert "Mutation" not in GRAPHQL_REGISTRY

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    create_schema(query=Query, mutation=Mutation)

    assert "Query" in GRAPHQL_REGISTRY
    assert isinstance(GRAPHQL_REGISTRY["Query"], GraphQLObjectType)

    assert "Mutation" in GRAPHQL_REGISTRY
    assert isinstance(GRAPHQL_REGISTRY["Mutation"], GraphQLObjectType)


def test_create_schema__descriptions() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        """Query description."""

        task = Entrypoint(TaskType)

    class Mutation(RootType):
        """Mutation description."""

        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=Mutation, description="Description.")

    assert schema.description == "Description."
    assert schema.query_type.description == "Query description."
    assert schema.mutation_type.description == "Mutation description."


def test_create_schema__extensions() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType, extensions={"foo": "2"}):
        task = Entrypoint(TaskType)

    class Mutation(RootType, extensions={"foo": "3"}):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(
        query=Query,
        mutation=Mutation,
        extensions={"foo": "1"},
    )

    assert schema.extensions == {"foo": "1"}
    assert schema.query_type.extensions == {"foo": "2", "undine_root_type": Query}
    assert schema.mutation_type.extensions == {"foo": "3", "undine_root_type": Mutation}


def test_create_schema__query_type_required() -> None:
    with pytest.raises(TypeError):
        create_schema()
