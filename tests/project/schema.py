from __future__ import annotations

from decimal import Decimal

from graphql import GraphQLObjectType, GraphQLSchema

from tests.example.models import Example
from undine import field


class Query:
    @field()
    def hello(self) -> str:
        """A simple field that returns a greeting."""
        return "Hello, World!"

    @field
    def hi(self, name: str) -> str:
        """
        A simple field that returns a greeting.

        Requires the name of the person to greet as an argument.

        :param name: The name of the person to greet.
        """
        return f"Hello, {name}!"

    @field
    def random(self, add: list[Decimal] | None = None) -> list[Decimal]:
        """A very random Decimal value."""
        return [Decimal("0.1"), Decimal("0.2"), Decimal("0.3"), *(add or ())]

    @field
    def examples(self) -> list[Example]:
        return Example.objects.all()


query = Query()

schema = GraphQLSchema(
    query=GraphQLObjectType(
        "Query",
        fields={
            "hello": query.hello,
            "hi": query.hi,
            "random": query.random,
            "examples": query.examples,
        },
    ),
)
