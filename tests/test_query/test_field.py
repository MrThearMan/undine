from __future__ import annotations

from graphql import GraphQLList, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from undine import Field, QueryType
from undine.resolvers import FunctionResolver, ModelFieldResolver


def test_field__simple():
    class MyQueryType(QueryType, model=Task):
        name = Field()

    field = MyQueryType.name

    assert repr(field) == "<undine.query.Field(ref=app.Task.name)>"

    assert field.ref == Task.name.field  # type: ignore[attr-defined]
    assert field.many is False
    assert field.nullable is False
    assert field.description is None
    assert field.deprecation_reason is None
    assert field.extensions == {"undine_field": field}

    assert field.owner == MyQueryType
    assert field.name == "name"

    resolver = field.get_resolver()
    assert isinstance(resolver, ModelFieldResolver)

    arguments = field.get_field_arguments()
    assert arguments == {}

    field_type = field.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert field_type.of_type == GraphQLString

    graphql_field = field.as_graphql_field()
    assert isinstance(graphql_field.type, GraphQLNonNull)
    assert graphql_field.type.of_type == GraphQLString
    assert graphql_field.args == arguments
    assert graphql_field.resolve == resolver
    assert graphql_field.description is None
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_field": field}


def test_field__function():
    class MyQueryType(QueryType, model=Task):
        @Field
        def custom(self, argument: str) -> list[str]:
            return [argument]

    field = MyQueryType.custom

    assert callable(field.ref)
    assert field.many is True
    assert field.nullable is False
    assert field.description is None
    assert field.deprecation_reason is None
    assert field.extensions == {"undine_field": field}

    assert field.owner == MyQueryType
    assert field.name == "custom"

    resolver = field.get_resolver()
    assert isinstance(resolver, FunctionResolver)

    arguments = field.get_field_arguments()
    assert sorted(arguments) == ["argument"]
    arg_type = arguments["argument"].type
    assert isinstance(arg_type, GraphQLNonNull)
    assert arg_type.of_type == GraphQLString

    field_type = field.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLList)
    assert isinstance(field_type.of_type.of_type, GraphQLNonNull)
    assert field_type.of_type.of_type.of_type == GraphQLString


def test_field__function__arguments():
    class MyQueryType(QueryType, model=Task):
        @Field(description="Description.")
        def custom(self, argument: str) -> list[str]:
            return [argument]

    field = MyQueryType.custom
    assert field.description == "Description."


def test_field__many():
    class MyQueryType(QueryType, model=Task):
        name = Field(many=True)

    field = MyQueryType.name
    assert field.many is True

    field_type = field.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLList)
    assert isinstance(field_type.of_type.of_type, GraphQLNonNull)
    assert field_type.of_type.of_type.of_type == GraphQLString


def test_field__nullable():
    class MyQueryType(QueryType, model=Task):
        name = Field(nullable=True)

    field = MyQueryType.name
    assert field.nullable is True

    field_type = field.get_field_type()
    assert field_type == GraphQLString


def test_field__nullable_and_many():
    class MyQueryType(QueryType, model=Task):
        name = Field(nullable=True, many=True)

    field = MyQueryType.name
    assert field.nullable is True
    assert field.many is True

    field_type = field.get_field_type()
    assert isinstance(field_type, GraphQLList)
    assert isinstance(field_type.of_type, GraphQLNonNull)
    assert field_type.of_type.of_type == GraphQLString


def test_field__description():
    class MyQueryType(QueryType, model=Task):
        name = Field(description="Description.")

    field = MyQueryType.name
    assert field.description == "Description."

    graphql_field = field.as_graphql_field()
    assert graphql_field.description == "Description."


def test_field__deprecation_reason():
    class MyQueryType(QueryType, model=Task):
        name = Field(deprecation_reason="Use something else.")

    field = MyQueryType.name
    assert field.deprecation_reason == "Use something else."

    graphql_field = field.as_graphql_field()
    assert graphql_field.deprecation_reason == "Use something else."


def test_field__extensions():
    class MyQueryType(QueryType, model=Task):
        name = Field(extensions={"foo": "bar"})

    field = MyQueryType.name
    assert field.extensions == {"foo": "bar", "undine_field": field}

    graphql_field = field.as_graphql_field()
    assert graphql_field.extensions == {"foo": "bar", "undine_field": field}
