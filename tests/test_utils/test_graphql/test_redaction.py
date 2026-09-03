from __future__ import annotations

from textwrap import dedent

from graphql import parse, print_ast, version_info

from undine.utils.graphql.redaction import redact_document, redact_variables


def test_redact_document__replaces_literal_values() -> None:
    document = parse("""
        query Login($password: String!) {
          a: user(email: "alice@example.com", age: 42, score: 1.5) { id }
          b: user(token: $password) { id }
        }
    """)

    assert redact_document(document) == dedent("""\
        query Login($password: String!) {
          a: user(email: "***", age: "***", score: "***") {
            id
          }
          b: user(token: $password) {
            id
          }
        }""")


def test_redact_document__replaces_values_inside_lists_and_objects() -> None:
    document = parse('{ search(filters: {names: ["Ada", "Grace"], limit: 10}, enabled: true) { id } }')

    expected = (
        dedent("""\
            {
              search(filters: { names: ["***", "***"], limit: "***" }, enabled: true) {
                id
              }
            }""")
        if version_info >= (3, 3, 0)
        else dedent("""\
            {
              search(filters: {names: ["***", "***"], limit: "***"}, enabled: true) {
                id
              }
            }""")
    )

    assert redact_document(document) == expected


def test_redact_document__does_not_modify_the_given_document() -> None:
    document = parse('{ user(email: "alice@example.com") { id } }')

    redact_document(document)

    assert print_ast(document) == dedent("""\
        {
          user(email: "alice@example.com") {
            id
          }
        }""")


def test_redact_variables__replaces_the_value_of_each_variable() -> None:
    variables = {"email": "alice@example.com", "age": 42, "enabled": True}

    assert redact_variables(variables) == {"email": "***", "age": "***", "enabled": "***"}


def test_redact_variables__keeps_only_the_top_level_keys() -> None:
    """The keys inside a variable can be client data, e.g. when the variable is a JSON scalar."""
    variables = {"filters": {"alice@example.com": ["Ada"]}, "values": ["Grace"]}

    assert redact_variables(variables) == {"filters": "***", "values": "***"}


def test_redact_variables__no_variables() -> None:
    assert redact_variables({}) == {}
