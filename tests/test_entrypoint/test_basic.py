from __future__ import annotations

from inspect import cleandoc

import pytest
from graphql import DirectiveLocation, GraphQLArgument, GraphQLInt, GraphQLNonNull, GraphQLString

from undine import Entrypoint, RootType
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError
from undine.resolvers import EntrypointFunctionResolver


def test_entrypoint__function() -> None:
    class Query(RootType):
        @Entrypoint
        def double(self, number: int) -> int:
            return number * 2

    assert repr(Query.double) == f"<undine.entrypoint.Entrypoint(ref={Query.double.ref})>"


def test_entrypoint__function__attributes() -> None:
    class Query(RootType):
        @Entrypoint
        def double(self, number: int) -> int:
            """Description."""
            return number * 2

    assert callable(Query.double.ref)
    assert Query.double.many is False
    assert Query.double.description == "Description."
    assert Query.double.deprecation_reason is None
    assert Query.double.extensions == {"undine_entrypoint": Query.double}
    assert Query.double.root_type == Query
    assert Query.double.name == "double"


def test_entrypoint__function__get_field_type() -> None:
    class Query(RootType):
        @Entrypoint
        def double(self, number: int) -> int:
            return number * 2

    field_type = Query.double.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLInt)


def test_entrypoint__function__get_field_arguments() -> None:
    class Query(RootType):
        @Entrypoint
        def double(self, number: int) -> int:
            return number * 2

    arguments = Query.double.get_field_arguments()
    assert arguments == {"number": GraphQLArgument(GraphQLNonNull(GraphQLInt), out_name="number")}


def test_entrypoint__function__get_resolver() -> None:
    class Query(RootType):
        @Entrypoint
        def double(self, number: int) -> int:
            return number * 2

    resolver = Query.double.get_resolver()
    assert isinstance(resolver, EntrypointFunctionResolver)


def test_entrypoint__function__as_graphql_field() -> None:
    class Query(RootType):
        @Entrypoint
        def double(self, number: int) -> int:
            """Description."""
            return number * 2

    graphql_field = Query.double.as_graphql_field()

    assert graphql_field.type == GraphQLNonNull(GraphQLInt)
    assert graphql_field.args == {"number": GraphQLArgument(GraphQLNonNull(GraphQLInt), out_name="number")}
    assert isinstance(graphql_field.resolve, EntrypointFunctionResolver)
    assert graphql_field.description == "Description."
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_entrypoint": Query.double}


def test_entrypoint__function__decorator_arguments() -> None:
    class Query(RootType):
        @Entrypoint(deprecation_reason="Use something else.")
        def double(self, number: int) -> int:
            return number * 2

    assert Query.double.deprecation_reason == "Use something else."


def test_entrypoint__function__directives__root_type() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.OBJECT], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class Query(RootType, directives=directives):
        @Entrypoint
        def double(self, number: int) -> int:
            return number * 2

    assert Query.__directives__ == directives

    assert str(Query) == cleandoc(
        """
        type Query @value(value: "foo") {
          double(
            number: Int!
          ): Int!
        }
        """
    )


def test_entrypoint__function__directives__root_type__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    with pytest.raises(DirectiveLocationError):

        class Query(RootType, directives=[ValueDirective(value="foo")]):
            @Entrypoint()
            def double(self, number: int) -> int:
                return number * 2


def test_entrypoint__function__directives__entrypoint() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class Query(RootType):
        @Entrypoint(directives=directives)
        def double(self, number: int) -> int:
            return number * 2

    assert Query.double.directives == directives

    assert str(Query) == cleandoc(
        """
        type Query {
          double(
            number: Int!
          ): Int! @value(value: "foo")
        }
        """
    )


def test_entrypoint__function__directives__entrypoint__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class Query(RootType):
            @Entrypoint(directives=directives)
            def double(self, number: int) -> int:
                return number * 2


def test_entrypoint__function__extensions__root_type() -> None:
    class Query(RootType, extensions={"foo": "bar"}):
        @Entrypoint
        def double(self, number: int) -> int:
            return number * 2

    assert Query.__extensions__ == {"foo": "bar", "undine_root_type": Query}


def test_entrypoint__function__extensions__entrypoint() -> None:
    class Query(RootType):
        @Entrypoint(extensions={"foo": "bar"})
        def double(self, number: int) -> int:
            return number * 2

    assert Query.double.extensions == {"foo": "bar", "undine_entrypoint": Query.double}


def test_entrypoint__function__str__root_type() -> None:
    class Query(RootType):
        @Entrypoint
        def double(self, number: int) -> int:
            return number * 2

    assert str(Query) == cleandoc(
        """
        type Query {
          double(
            number: Int!
          ): Int!
        }
        """
    )


def test_entrypoint__function__str__entrypoint() -> None:
    class Query(RootType):
        @Entrypoint
        def double(self, number: int) -> int:
            return number * 2

    assert str(Query.double) == cleandoc(
        """
        double(
          number: Int!
        ): Int!
        """
    )
