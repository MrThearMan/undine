from __future__ import annotations

from graphql import DirectiveLocation

from undine import Entrypoint, RootType, create_schema
from undine.directives import Directive


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
