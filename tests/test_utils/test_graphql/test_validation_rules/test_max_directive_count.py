from __future__ import annotations

from graphql import DirectiveLocation

from undine import Directive, Entrypoint, RootType, create_schema


def test_validation_rules__max_directive_count(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_DIRECTIVES = 0

    class NewDirective(Directive, locations=[DirectiveLocation.FIELD], schema_name="new"): ...

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            example @new
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "Operation has more than 0 directives, which exceeds the maximum allowed.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_directive_count__at_limit(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_DIRECTIVES = 1

    class NewDirective(Directive, locations=[DirectiveLocation.FIELD], schema_name="new"): ...

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            example @new
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors


def test_validation_rules__max_directive_count__fragment_spread(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_DIRECTIVES = 0

    class NewDirective(Directive, locations=[DirectiveLocation.FIELD], schema_name="new"): ...

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        fragment ExampleFrag on Query {
            example @new
        }
        query {
            ...ExampleFrag
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "Operation has more than 0 directives, which exceeds the maximum allowed.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_directive_count__fragment_spread__already_visited(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_DIRECTIVES = 1

    class NewDirective(Directive, locations=[DirectiveLocation.FIELD], schema_name="new"): ...

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        fragment ExampleFrag on Query {
            example @new
        }
        query {
            ...ExampleFrag
            ...ExampleFrag
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors


def test_validation_rules__max_directive_count__fragment_definition(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_DIRECTIVES = 0

    class NewDirective(Directive, locations=[DirectiveLocation.FRAGMENT_DEFINITION], schema_name="new"): ...

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        fragment ExampleFrag on Query @new {
            example
        }
        query {
            ...ExampleFrag
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "Operation has more than 0 directives, which exceeds the maximum allowed.",
            "extensions": {"status_code": 400},
        }
    ]
