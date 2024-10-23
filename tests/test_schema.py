from typing import Any

from graphql import ExecutionResult, GraphQLObjectType, GraphQLSchema, GraphQLString
from graphql.type.definition import GraphQLField, GraphQLNonNull

from example_project.app.models import Task
from tests.helpers import override_undine_settings
from undine import Entrypoint, MutationType, QueryType, create_schema
from undine.schema import execute_graphql
from undine.typing import GraphQLParams


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


@override_undine_settings(SCHEMA="undine.settings.example_schema")
def test_execute_graphql():
    params = GraphQLParams(query="query { hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result == ExecutionResult(data={"hello": "Hello, World!"})


invalid_schema = GraphQLSchema(
    query=GraphQLObjectType(
        "Query",
        fields={
            "__hello": GraphQLField(
                GraphQLString,
                resolve=lambda obj, info: "Hello, World!",  # noqa: ARG005
            )
        },
    ),
)


@override_undine_settings(SCHEMA="tests.test_schema.invalid_schema")
def test_execute_graphql__schema_error():
    params = GraphQLParams(query="query { __hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == (
        "Name '__hello' must not begin with '__', which is reserved by GraphQL introspection."
    )


@override_undine_settings(SCHEMA="undine.settings.example_schema")
def test_execute_graphql__parse_error():
    params = GraphQLParams(query="query { €hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "Syntax Error: Unexpected character: U+20AC."


@override_undine_settings(SCHEMA="undine.settings.example_schema")
def test_execute_graphql__non_query_operation_on_get_request():
    params = GraphQLParams(query="mutation { hello }")
    result = execute_graphql(params=params, method="GET", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "Only query operations are allowed on GET requests."
    assert result.errors[0].extensions == {"status_code": 405}


@override_undine_settings(SCHEMA="undine.settings.example_schema")
def test_execute_graphql__validation_error():
    params = GraphQLParams(query="query { hello } query { hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "This anonymous operation must be the only defined operation."


def _raise_value_error(*args: Any, **kwargs: Any) -> Any:
    msg = "Error!"
    raise ValueError(msg)


error_schema = GraphQLSchema(
    query=GraphQLObjectType(
        "Query",
        fields={
            "hello": GraphQLField(
                GraphQLNonNull(GraphQLString),
                resolve=_raise_value_error,
            )
        },
    ),
)


@override_undine_settings(SCHEMA="tests.test_schema.error_schema")
def test_execute_graphql__unexpected():
    params = GraphQLParams(query="query { hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "Error!"
    assert result.errors[0].extensions == {"status_code": 400}
