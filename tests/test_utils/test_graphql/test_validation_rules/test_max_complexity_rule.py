from __future__ import annotations

import pytest

from example_project.app.models import Task, TaskTypeChoices
from undine import Entrypoint, Field, MutationType, QueryType, RootType, create_schema
from undine.relay import Connection


def test_validation_rules__max_complexity_rule__entrypoint__function(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 0

    class Query(RootType):
        @Entrypoint(complexity=1)
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            example
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "Query complexity of 1 exceeds the maximum allowed complexity of 0.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__max_complexity_rule__entrypoint__mutation(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskCreateMutation, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation, complexity=1)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
            createTask(input: $input) {
                name
            }
        }
    """

    input_data = {
        "name": "foo",
        "type": TaskTypeChoices.TASK,
    }
    response = graphql(query, variables={"input": input_data})

    assert response.errors == [
        {
            "message": "Query complexity of 1 exceeds the maximum allowed complexity of 0.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__max_complexity_rule__entrypoint__mutation__query_type(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field(complexity=1)

    class TaskCreateMutation(MutationType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskCreateMutation, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
            createTask(input: $input) {
                name
            }
        }
    """

    input_data = {
        "name": "foo",
        "type": TaskTypeChoices.TASK,
    }
    response = graphql(query, variables={"input": input_data})

    assert response.errors == [
        {
            "message": "Query complexity of 1 exceeds the maximum allowed complexity of 0.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_complexity_rule__query_type__field(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 0

    class TaskType(QueryType[Task], auto=True):
        name = Field(complexity=1)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                name
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "Query complexity of 1 exceeds the maximum allowed complexity of 0.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_complexity_rule__query_type__field__entrypoint(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 1

    class TaskType(QueryType[Task], auto=True):
        name = Field(complexity=1)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True, complexity=1)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                name
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "Query complexity of 2 exceeds the maximum allowed complexity of 1.",
            "extensions": {"status_code": 400},
        },
    ]


def test_validation_rules__max_complexity_rule__query_type__field__connection(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 0

    class TaskType(QueryType[Task], auto=True):
        name = Field(complexity=1)

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                edges {
                    node {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "Query complexity of 1 exceeds the maximum allowed complexity of 0.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_complexity_rule__at_limit(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 1

    class Query(RootType):
        @Entrypoint(complexity=1)
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            example
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_validation_rules__max_complexity_rule__fragment_spread__already_visited(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 1

    class TaskType(QueryType[Task], auto=False):
        name = Field(complexity=1)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        fragment TaskFrag on TaskType {
            name
        }
        query {
            tasks {
                ...TaskFrag
                ...TaskFrag
            }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors


def test_validation_rules__max_complexity_rule__inline_fragment(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field(complexity=1)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                ... on TaskType {
                    name
                }
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "Query complexity of 1 exceeds the maximum allowed complexity of 0.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_complexity_rule__inline_fragment__no_type_condition(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field(complexity=1)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                ... {
                    name
                }
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "Query complexity of 1 exceeds the maximum allowed complexity of 0.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_complexity_rule__fragment_spread__not_found(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 100

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            ...UndefinedFrag
        }
    """

    response = graphql(query)
    assert response.has_errors is True
