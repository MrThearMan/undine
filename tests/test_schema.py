from graphql import GraphQLObjectType

from example_project.app.models import Task
from undine import Entrypoint, MutationType, QueryType, create_schema


def test_create_schema():
    class TaskType(QueryType, model=Task, auto=False): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Query:
        task = Entrypoint(TaskType)

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query_class=Query, mutation_class=Mutation)

    assert isinstance(schema.query_type, GraphQLObjectType)
    assert schema.query_type.name == "Query"
    assert sorted(schema.query_type.fields) == ["task"]

    assert isinstance(schema.mutation_type, GraphQLObjectType)
    assert schema.mutation_type.name == "Mutation"
    assert sorted(schema.mutation_type.fields) == ["createTask"]


def test_create_schema__descriptions():
    class TaskType(QueryType, model=Task, auto=False): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Query:
        """Query description."""

        task = Entrypoint(TaskType)

    class Mutation:
        """Mutation description."""

        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query_class=Query, mutation_class=Mutation, schema_description="Description.")

    assert schema.description == "Description."
    assert schema.query_type.description == "Query description."
    assert schema.mutation_type.description == "Mutation description."


def test_create_schema__extensions():
    class TaskType(QueryType, model=Task, auto=False): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Query:
        """Query description."""

        task = Entrypoint(TaskType)

    class Mutation:
        """Mutation description."""

        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(
        query_class=Query,
        mutation_class=Mutation,
        schema_extensions={"foo": "1"},
        query_extensions={"foo": "2"},
        mutation_extensions={"foo": "3"},
    )

    assert schema.extensions == {"foo": "1"}
    assert schema.query_type.extensions == {"foo": "2"}
    assert schema.mutation_type.extensions == {"foo": "3"}


def test_create_schema__nullable():
    schema = create_schema()

    assert schema.query_type is None
    assert schema.mutation_type is None
