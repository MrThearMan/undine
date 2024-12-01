from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import GraphQLArgument, GraphQLList, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo
from undine import Field, QueryType
from undine.optimizer.optimizer import QueryOptimizer
from undine.resolvers import FunctionResolver, ModelFieldResolver

if TYPE_CHECKING:
    from undine.typing import GQLInfo


def test_field__repr():
    class MyQueryType(QueryType, model=Task):
        name = Field()

    assert repr(MyQueryType.name) == "<undine.query.Field(ref=app.Task.name)>"


def test_field__attributes():
    class MyQueryType(QueryType, model=Task):
        name = Field()

    assert MyQueryType.name.ref == Task._meta.get_field("name")
    assert MyQueryType.name.many is False
    assert MyQueryType.name.nullable is False
    assert MyQueryType.name.description is None
    assert MyQueryType.name.resolver_func is None
    assert MyQueryType.name.deprecation_reason is None
    assert MyQueryType.name.extensions == {"undine_field": MyQueryType.name}
    assert MyQueryType.name.owner == MyQueryType
    assert MyQueryType.name.name == "name"


def test_field__get_resolver():
    class MyQueryType(QueryType, model=Task):
        name = Field()

    resolver = MyQueryType.name.get_resolver()
    assert isinstance(resolver, ModelFieldResolver)


def test_field__resolver():
    class MyQueryType(QueryType, model=Task):
        name = Field()

        @name.resolve
        def resolver_func(self) -> str:
            return "foo"

    resolver = MyQueryType.name.get_resolver()
    assert isinstance(resolver, FunctionResolver)
    assert resolver.func == MyQueryType.resolver_func

    assert resolver(root=None, info=MockGQLInfo()) == "foo"


def test_field__optimize():
    class MyQueryType(QueryType, model=Task):
        name = Field()

        @name.optimize
        def optimize_name(self: Field, optimizer: QueryOptimizer) -> int:
            return 1

    field = MyQueryType.name
    optimizer = QueryOptimizer(None, MockGQLInfo())
    assert field.optimizer_func(field, optimizer) == 1


def test_field__permissions():
    class MyQueryType(QueryType, model=Task):
        name = Field()

        @name.permissions
        def name_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return True

    task = TaskFactory.build(name="Test task")

    field = MyQueryType.name
    assert field.permissions_func(field, MockGQLInfo(), task) is True


def test_field__get_field_arguments():
    class MyQueryType(QueryType, model=Task):
        name = Field()

    arguments = MyQueryType.name.get_field_arguments()
    assert arguments == {}


def test_field__get_field_type():
    class MyQueryType(QueryType, model=Task):
        name = Field()

    field_type = MyQueryType.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLString)


def test_field__as_graphql_field():
    class MyQueryType(QueryType, model=Task):
        name = Field()

    graphql_field = MyQueryType.name.as_graphql_field()
    assert graphql_field.type == GraphQLNonNull(GraphQLString)
    assert graphql_field.args == {}
    assert isinstance(graphql_field.resolve, ModelFieldResolver)
    assert graphql_field.description is None
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_field": MyQueryType.name}


def test_field__function__repr():
    class MyQueryType(QueryType, model=Task):
        @Field
        def custom(self, argument: str) -> list[str]:
            """Description."""
            return [argument]

    assert repr(MyQueryType.custom) == f"<undine.query.Field(ref={MyQueryType.custom.ref})>"


def test_field__function__attributes():
    class MyQueryType(QueryType, model=Task):
        @Field
        def custom(self, argument: str) -> list[str]:
            """Description."""
            return [argument]

    assert callable(MyQueryType.custom.ref)
    assert MyQueryType.custom.many is True
    assert MyQueryType.custom.nullable is False
    assert MyQueryType.custom.description == "Description."
    assert MyQueryType.custom.deprecation_reason is None
    assert MyQueryType.custom.extensions == {"undine_field": MyQueryType.custom}
    assert MyQueryType.custom.owner == MyQueryType
    assert MyQueryType.custom.name == "custom"


def test_field__function__get_resolver():
    class MyQueryType(QueryType, model=Task):
        @Field
        def custom(self, argument: str) -> list[str]:
            """Description."""
            return [argument]

    resolver = MyQueryType.custom.get_resolver()
    assert isinstance(resolver, FunctionResolver)


def test_field__function__get_field_arguments():
    class MyQueryType(QueryType, model=Task):
        @Field
        def custom(self, argument: str) -> list[str]:
            """Description."""
            return [argument]

    arguments = MyQueryType.custom.get_field_arguments()
    assert arguments == {"argument": GraphQLArgument(GraphQLNonNull(GraphQLString))}


def test_field__function__get_field_type():
    class MyQueryType(QueryType, model=Task):
        @Field
        def custom(self, argument: str) -> list[str]:
            """Description."""
            return [argument]

    field_type = MyQueryType.custom.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


def test_field__function__decorator_arguments():
    class MyQueryType(QueryType, model=Task):
        @Field(deprecation_reason="Use something else.")
        def custom(self, argument: str) -> list[str]:
            return [argument]

    assert MyQueryType.custom.deprecation_reason == "Use something else."


def test_field__many():
    class MyQueryType(QueryType, model=Task):
        name = Field(many=True)

    assert MyQueryType.name.many is True


def test_field__many__get_field_type():
    class MyQueryType(QueryType, model=Task):
        name = Field(many=True)

    field_type = MyQueryType.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


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
    assert field_type == GraphQLList(GraphQLNonNull(GraphQLString))


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


# TODO: Field with expression. Check optimizer func.
