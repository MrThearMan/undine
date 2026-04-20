from __future__ import annotations

from graphql import DirectiveLocation, ValidationContext, build_ast_schema, parse
from graphql.language.ast import (
    DirectiveNode,
    FieldNode,
    FragmentDefinitionNode,
    NamedTypeNode,
    NameNode,
    SelectionSetNode,
    VariableDefinitionNode,
    VariableNode,
)

from undine import Directive, Entrypoint, RootType, create_schema
from undine.utils.graphql.validation_rules.max_directive_count import MaxDirectiveCountRule


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

    # Using the same fragment twice should not double-count the directive
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


def test_validation_rules__max_directive_count__fragment_variable_directives(undine_settings) -> None:
    schema = build_ast_schema(parse("type Query { field: String }"))
    doc = parse("query { field }")
    ctx = ValidationContext(schema=schema, ast=doc, type_info=None, on_error=lambda _: None)
    rule = MaxDirectiveCountRule(ctx)

    # Construct a VariableDefinitionNode with a directive
    var_def = VariableDefinitionNode(
        variable=VariableNode(name=NameNode(value="x")),
        type=NamedTypeNode(name=NameNode(value="String")),
        directives=(DirectiveNode(name=NameNode(value="deprecated"), arguments=()),),
    )
    frag = FragmentDefinitionNode(
        name=NameNode(value="Frag"),
        type_condition=NamedTypeNode(name=NameNode(value="Query")),
        selection_set=SelectionSetNode(selections=()),
        variable_definitions=(var_def,),
        directives=(),
    )

    count = rule.count_directives(frag)
    assert count == 1  # One directive on the variable definition


def test_max_directive_count__count_directives__fragment_definition_node() -> None:
    schema = build_ast_schema(parse("type Query { field: String }"))
    doc = parse("query { field }")
    ctx = ValidationContext(schema=schema, ast=doc, type_info=None, on_error=lambda _: None)
    rule = MaxDirectiveCountRule(ctx)

    directive_field = FieldNode(
        name=NameNode(value="field"),
        alias=None,
        arguments=(),
        directives=(DirectiveNode(name=NameNode(value="skip"), arguments=()),),
        selection_set=None,
    )
    frag = FragmentDefinitionNode(
        name=NameNode(value="Frag"),
        type_condition=NamedTypeNode(name=NameNode(value="Query")),
        selection_set=SelectionSetNode(selections=(directive_field,)),
        variable_definitions=(),
        directives=(DirectiveNode(name=NameNode(value="deprecated"), arguments=()),),
    )

    count = rule.count_directives(frag)
    assert count == 2  # One on the fragment, one on the field inside it


def test_max_directive_count__count_directives__no_match_fallthrough() -> None:
    schema = build_ast_schema(parse("type Query { field: String }"))
    doc = parse("query { field }")
    ctx = ValidationContext(schema=schema, ast=doc, type_info=None, on_error=lambda _: None)
    rule = MaxDirectiveCountRule(ctx)

    # Pass something that matches none of the match cases → falls through to return 0
    count = rule.count_directives(NameNode(value="dummy"))
    assert count == 0
