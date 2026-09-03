from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import StringValueNode, Visitor, print_ast, visit

if TYPE_CHECKING:
    from graphql import DocumentNode

__all__ = [
    "REDACTED_VALUE",
    "redact_document",
    "redact_variables",
]


REDACTED_VALUE: str = "***"
"""Value that replaces literal values in a redacted GraphQL document."""


def redact_document(document: DocumentNode) -> str:
    """
    Print the given GraphQL document with all literal values replaced with `REDACTED_VALUE`.

    A client can hardcode an argument in the document instead of passing it as a variable,
    so the document can contain sensitive data. Redacting keeps the structure of the document,
    which is what makes it useful for grouping operations, but removes the values.
    """
    redacted_document = visit(document, LiteralRedactionVisitor())
    return print_ast(redacted_document)


def redact_variables(variables: dict[str, Any]) -> dict[str, str]:
    """
    Replace the value of each variable with `REDACTED_VALUE`.

    Knowing which variables a client sent says something about the operation, while the values
    are the client's data. Only the top-level keys are kept, since the keys inside a variable
    can be client data as well, e.g. when the variable is typed as a JSON scalar.
    """
    return dict.fromkeys(variables, REDACTED_VALUE)


class LiteralRedactionVisitor(Visitor):
    """Replaces all scalar literal values in a GraphQL document with `REDACTED_VALUE`."""

    def enter_string_value(self, *args: Any) -> StringValueNode:
        return StringValueNode(value=REDACTED_VALUE)

    def enter_int_value(self, *args: Any) -> StringValueNode:
        return StringValueNode(value=REDACTED_VALUE)

    def enter_float_value(self, *args: Any) -> StringValueNode:
        return StringValueNode(value=REDACTED_VALUE)
