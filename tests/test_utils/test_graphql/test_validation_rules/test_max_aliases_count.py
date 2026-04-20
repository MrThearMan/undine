from __future__ import annotations

from graphql import ValidationContext, build_ast_schema, parse
from graphql.language.ast import FieldNode, FragmentDefinitionNode, NamedTypeNode, NameNode, SelectionSetNode

from undine import Entrypoint, RootType, create_schema
from undine.utils.graphql.validation_rules.max_alias_count import MaxAliasCountRule


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


def test_validation_rules__max_aliases_count__fragment_spread(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_ALIASES = 0

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        fragment ExampleFrag on Query {
            alias: example
        }
        query {
            ...ExampleFrag
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "Operation has more than 0 aliases, which exceeds the maximum allowed.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_aliases_count__fragment_spread__already_visited(graphql, undine_settings) -> None:
    undine_settings.MAX_ALLOWED_ALIASES = 1

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    # Using the same fragment twice should not double-count the alias
    query = """
        fragment ExampleFrag on Query {
            alias: example
        }
        query {
            ...ExampleFrag
            ...ExampleFrag
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors


def test_max_alias_count__count_aliases__fragment_definition_node() -> None:
    schema = build_ast_schema(parse("type Query { field: String }"))
    doc = parse("query { field }")
    ctx = ValidationContext(schema=schema, ast=doc, type_info=None, on_error=lambda _: None)
    rule = MaxAliasCountRule(ctx)

    aliased_field = FieldNode(
        name=NameNode(value="field"),
        alias=NameNode(value="aliasedField"),
        arguments=(),
        directives=(),
        selection_set=None,
    )
    frag = FragmentDefinitionNode(
        name=NameNode(value="Frag"),
        type_condition=NamedTypeNode(name=NameNode(value="Query")),
        selection_set=SelectionSetNode(selections=(aliased_field,)),
        variable_definitions=(),
        directives=(),
    )

    count = rule.count_aliases(frag)
    assert count == 1


def test_max_alias_count__count_aliases__no_match_fallthrough() -> None:
    schema = build_ast_schema(parse("type Query { field: String }"))
    doc = parse("query { field }")
    ctx = ValidationContext(schema=schema, ast=doc, type_info=None, on_error=lambda _: None)
    rule = MaxAliasCountRule(ctx)

    # Pass something that matches none of the match cases → falls through to return 0

    count = rule.count_aliases(NameNode(value="dummy"))
    assert count == 0
