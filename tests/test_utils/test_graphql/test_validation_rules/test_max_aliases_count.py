from __future__ import annotations

from undine import Entrypoint, RootType, create_schema


def test_validation_rules__max_aliases_count(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_ALIASES = 0

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            alias: example
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "Operation has more than 0 aliases, which exceeds the maximum allowed.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_aliases_count__at_limit(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_ALIASES = 1

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            alias: example
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
