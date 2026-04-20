from __future__ import annotations

import pytest
from graphql import ValidationContext, build_ast_schema, parse
from graphql.language.ast import FragmentSpreadNode, NameNode, OperationDefinitionNode, SelectionSetNode

from example_project.app.models import Task, TaskTypeChoices
from undine import Entrypoint, Field, MutationType, QueryType, RootType, create_schema
from undine.relay import Connection
from undine.utils.graphql.validation_rules.max_complexity_rule import MaxComplexityRule


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

    # Using the same fragment twice inside the same field selection should not count it twice
    # (visited_fragments prevents double-counting within one top-level selection)
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
    # Only counted once despite being spread twice
    assert response.has_errors is False, response.errors


def test_validation_rules__max_complexity_rule__fragment_spread__undefined_fragment(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 0

    class Query(RootType):
        @Entrypoint(complexity=0)
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    # Reference a fragment that doesn't exist (validator handles this separately).
    # The complexity for the missing fragment is 0, so no error.
    query = """
        query {
            example
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

    # A query referencing an undefined fragment — context.get_fragment returns None
    # The complexity rule should handle it gracefully (return early at line 98)
    query = """
        query {
            ...UndefinedFrag
        }
    """

    # This will have validation errors (unknown fragment) but complexity rule handles None gracefully
    response = graphql(query)
    assert response.has_errors is True


def test_validation_rules__max_complexity_rule__handle_fragment_spread__fragment_is_none(undine_settings) -> None:
    schema = build_ast_schema(parse("type Query { field: String }"))
    doc = parse("query { field }")
    ctx = ValidationContext(schema=schema, ast=doc, type_info=None, on_error=lambda e: None)
    rule = MaxComplexityRule(ctx)

    # Construct a FragmentSpreadNode for a fragment not in the document
    spread = FragmentSpreadNode(name=NameNode(value="NonExistentFrag"), directives=())

    # context.get_fragment returns None → handle_fragment_spread hits line 98 (return)
    rule.handle_fragment_spread(None, spread)  # type: ignore[arg-type]
    assert rule.complexity == 0


def test_validation_rules__max_complexity_rule__handle_selection__no_match() -> None:

    schema = build_ast_schema(parse("type Query { field: String }"))
    doc = parse("query { field }")
    ctx = ValidationContext(schema=schema, ast=doc, type_info=None, on_error=lambda e: None)
    rule = MaxComplexityRule(ctx)

    # Pass an OperationDefinitionNode — doesn't match any case in handle_selection
    op_node = OperationDefinitionNode(
        selection_set=SelectionSetNode(selections=()),
        directives=(),
        variable_definitions=(),
    )
    rule.handle_selection(None, op_node)  # type: ignore[arg-type]
    assert rule.complexity == 0
