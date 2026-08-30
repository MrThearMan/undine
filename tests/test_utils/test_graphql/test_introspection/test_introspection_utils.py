from __future__ import annotations

import pytest
from graphql import (
    DirectiveLocation,
    GraphQLArgument,
    GraphQLDirective,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLString,
)

from undine import Entrypoint, RootType, create_schema
from undine.utils.graphql.introspection import (
    _root_type_visible,  # noqa: PLC2701
    resolve_directive_args,
    resolve_directive_description,
    resolve_directive_is_repeatable,
    resolve_field_args,
    resolve_field_description,
    resolve_schema_description,
    resolve_schema_mutation_type,
    resolve_schema_query_type,
    resolve_schema_subscription_type,
    resolve_type_description,
    resolve_type_enum_values,
    resolve_type_fields,
    resolve_type_input_fields,
    resolve_type_is_one_of,
    resolve_type_meta_field_def,
    resolve_type_specified_by_url,
)


class _FakeContext:
    """Stand-in for `GQLContext` outside a request, where visibility checks have no request to consult."""

    request = None


class _FakeInfo:
    """Bare stand-in for `GraphQLResolveInfo` usable by the introspection resolvers."""

    context = _FakeContext()
    schema: GraphQLSchema | None = None


def test_resolve_schema_description() -> None:
    schema = GraphQLSchema(
        query=GraphQLObjectType("Query", fields={"x": GraphQLField(GraphQLString)}),
        description="My schema",
    )
    assert resolve_schema_description(schema, None) == "My schema"


def test_resolve_schema_query_type__none_when_schema_has_no_query() -> None:
    schema = GraphQLSchema(
        query=GraphQLObjectType("Q", fields={"x": GraphQLField(GraphQLString)}),
    )
    # Clear the query type to hit the "root.query_type is None" branch.
    schema.query_type = None  # type: ignore[assignment]

    assert resolve_schema_query_type(schema, _FakeInfo()) is None


def test_resolve_schema_mutation_type__none_when_schema_has_no_mutation() -> None:
    schema = GraphQLSchema(
        query=GraphQLObjectType("Q", fields={"x": GraphQLField(GraphQLString)}),
    )

    assert resolve_schema_mutation_type(schema, _FakeInfo()) is None


def test_resolve_schema_subscription_type__none_when_schema_has_no_subscription() -> None:
    schema = GraphQLSchema(
        query=GraphQLObjectType("Q", fields={"x": GraphQLField(GraphQLString)}),
    )

    assert resolve_schema_subscription_type(schema, _FakeInfo()) is None


def test_resolve_directive_description() -> None:
    directive = GraphQLDirective("foo", [DirectiveLocation.FIELD], description="desc")
    assert resolve_directive_description(directive, None) == "desc"


def test_resolve_directive_is_repeatable() -> None:
    directive = GraphQLDirective("foo", [DirectiveLocation.FIELD], is_repeatable=True)
    assert resolve_directive_is_repeatable(directive, None) is True


def test_resolve_directive_args__include_deprecated() -> None:
    arg = GraphQLArgument(GraphQLString, deprecation_reason="old")
    directive = GraphQLDirective("foo", [DirectiveLocation.FIELD], args={"x": arg})

    result = resolve_directive_args(directive, _FakeInfo(), includeDeprecated=True)
    assert len(result) == 1


def test_resolve_type_description() -> None:
    gql_type = GraphQLObjectType("Foo", fields={"x": GraphQLField(GraphQLString)}, description="bar")
    assert resolve_type_description(gql_type, None) == "bar"


def test_resolve_type_specified_by_url() -> None:
    scalar = GraphQLScalarType("MyScalar", specified_by_url="https://example.com/")
    assert resolve_type_specified_by_url(scalar, None) == "https://example.com/"


def test_resolve_type_fields__include_deprecated() -> None:
    gql_type = GraphQLObjectType(
        "FooWithDeprecated",
        fields={
            "active": GraphQLField(GraphQLString),
            "old": GraphQLField(GraphQLString, deprecation_reason="use active"),
        },
    )

    result = resolve_type_fields(gql_type, _FakeInfo(), includeDeprecated=True)
    assert result is not None
    assert len(result) == 2


def test_resolve_type_fields__exclude_deprecated() -> None:
    gql_type = GraphQLObjectType(
        "FooExcludeDeprecated",
        fields={
            "active": GraphQLField(GraphQLString),
            "old": GraphQLField(GraphQLString, deprecation_reason="use active"),
        },
    )

    result = resolve_type_fields(gql_type, _FakeInfo(), includeDeprecated=False)
    assert result is not None
    assert len(result) == 1
    assert result[0][0] == "active"


def test_resolve_type_enum_values__include_deprecated() -> None:
    gql_type = GraphQLEnumType(
        "MyEnumAll",
        values={
            "A": GraphQLEnumValue("A"),
            "B": GraphQLEnumValue("B", deprecation_reason="old"),
        },
    )

    result = resolve_type_enum_values(gql_type, _FakeInfo(), includeDeprecated=True)
    assert result is not None
    assert len(result) == 2


def test_resolve_type_enum_values__exclude_deprecated() -> None:
    gql_type = GraphQLEnumType(
        "MyEnumFiltered",
        values={
            "A": GraphQLEnumValue("A"),
            "B": GraphQLEnumValue("B", deprecation_reason="old"),
        },
    )

    result = resolve_type_enum_values(gql_type, _FakeInfo(), includeDeprecated=False)
    assert result is not None
    assert len(result) == 1
    assert result[0][0] == "A"


def test_resolve_type_input_fields__include_deprecated() -> None:
    gql_type = GraphQLInputObjectType(
        "MyInput",
        fields={
            "active": GraphQLInputField(GraphQLString),
            "old": GraphQLInputField(GraphQLString, deprecation_reason="use active"),
        },
    )

    result = resolve_type_input_fields(gql_type, _FakeInfo(), includeDeprecated=True)
    assert result is not None
    assert len(result) == 2


def test_resolve_type_is_one_of__input_type() -> None:
    gql_type = GraphQLInputObjectType("MyInput", fields={"x": GraphQLInputField(GraphQLString)}, is_one_of=True)
    assert resolve_type_is_one_of(gql_type, None) is True


def test_resolve_type_is_one_of__non_input_type() -> None:
    gql_type = GraphQLObjectType("Foo", fields={"x": GraphQLField(GraphQLString)})
    assert resolve_type_is_one_of(gql_type, None) is None


def test_resolve_field_description() -> None:
    item = ("myField", GraphQLField(GraphQLString, description="a field"))
    assert resolve_field_description(item, None) == "a field"


def test_resolve_field_args__include_deprecated() -> None:
    arg = GraphQLArgument(GraphQLString, deprecation_reason="old")
    field = GraphQLField(GraphQLString, args={"x": arg})
    item = ("myField", field)

    result = resolve_field_args(item, _FakeInfo(), includeDeprecated=True)
    assert len(result) == 1


@pytest.mark.django_db
def test_resolve_type_meta_field_def__type_not_found(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    info = _FakeInfo()
    info.schema = undine_settings.SCHEMA

    result = resolve_type_meta_field_def(None, info, name="NonExistentType")
    assert result is None


def test_root_type_visible__no_undine_wrapper_returns_true() -> None:
    plain_object = GraphQLObjectType("Plain", fields={"x": GraphQLField(GraphQLString)})

    assert _root_type_visible(plain_object, _FakeInfo()) is True
