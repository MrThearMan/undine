from __future__ import annotations

import pytest
from django.db.models import Count, Value
from django.db.models.functions import Upper
from graphql import DirectiveLocation, GraphQLArgument, GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Calculation, CalculationArgument, DjangoExpression, Field, GQLInfo, QueryType
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError, GraphQLPermissionError
from undine.optimizer.optimizer import OptimizationData
from undine.query import QueryTypeMeta
from undine.resolvers import FieldFunctionResolver, ModelAttributeResolver
from undine.typing import OptimizerFunc


def test_field__repr() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

    assert repr(MyQueryType.name) == "<undine.query.Field(ref=<django.db.models.fields.CharField: name>)>"


def test_field__repr__function() -> None:
    class MyQueryType(QueryType[Task]):
        @Field
        def custom(self) -> list[str]:
            """Description."""
            return []

    assert repr(MyQueryType.custom) == f"<undine.query.Field(ref={MyQueryType.custom.ref})>"


def test_field__str() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

    assert str(MyQueryType.name) == "name: String!"


def test_field__attributes() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

    assert MyQueryType.name.ref == Task._meta.get_field("name")
    assert MyQueryType.name.many is False
    assert MyQueryType.name.nullable is False
    assert MyQueryType.name.description is None
    assert MyQueryType.name.deprecation_reason is None
    assert MyQueryType.name.schema_name == "name"
    assert MyQueryType.name.directives == []
    assert MyQueryType.name.extensions == {"undine_field": MyQueryType.name}

    assert MyQueryType.name.resolver_func is None
    assert MyQueryType.name.optimizer_func is None
    assert MyQueryType.name.permissions_func is None

    assert MyQueryType.name.query_type == MyQueryType
    assert MyQueryType.name.name == "name"


def test_field__attributes__function() -> None:
    class MyQueryType(QueryType[Task]):
        @Field
        def custom(self, argument: str) -> list[str]:
            return []

    assert callable(MyQueryType.custom.ref)
    assert MyQueryType.custom.many is True
    assert MyQueryType.custom.nullable is False
    assert MyQueryType.custom.description is None
    assert MyQueryType.custom.deprecation_reason is None
    assert MyQueryType.custom.schema_name == "custom"
    assert MyQueryType.custom.directives == []
    assert MyQueryType.custom.extensions == {"undine_field": MyQueryType.custom}

    assert MyQueryType.custom.resolver_func is None
    assert MyQueryType.custom.optimizer_func is None
    assert MyQueryType.custom.permissions_func is None

    assert MyQueryType.custom.query_type == MyQueryType
    assert MyQueryType.custom.name == "custom"


def test_field__attributes__function__decorator_arguments() -> None:
    class MyQueryType(QueryType[Task]):
        @Field(deprecation_reason="Use something else.")
        def custom(self) -> list[str]:
            return []

    assert MyQueryType.custom.deprecation_reason == "Use something else."


def test_field__as_graphql_field() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

    graphql_field = MyQueryType.name.as_graphql_field()

    assert graphql_field.type == GraphQLNonNull(GraphQLString)
    assert graphql_field.args == {}
    assert isinstance(graphql_field.resolve, ModelAttributeResolver)
    assert graphql_field.description is None
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_field": MyQueryType.name}


def test_field__get_field_type() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

    field_type = MyQueryType.name.get_field_type()

    assert field_type == GraphQLNonNull(GraphQLString)


def test_field__get_field_type__function() -> None:
    class MyQueryType(QueryType[Task]):
        @Field
        def custom(self) -> list[str]:
            return []

    field_type = MyQueryType.custom.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


def test_field__get_field_arguments() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

    arguments = MyQueryType.name.get_field_arguments()

    assert arguments == {}


def test_field__get_field_arguments__function() -> None:
    class MyQueryType(QueryType[Task]):
        @Field
        def custom(self, argument: str) -> list[str]:
            return [argument]

    arguments = MyQueryType.custom.get_field_arguments()
    assert arguments == {
        "argument": GraphQLArgument(GraphQLNonNull(GraphQLString), out_name="argument"),
    }


def test_field__get_resolver() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

    resolver = MyQueryType.name.get_resolver()

    assert isinstance(resolver, ModelAttributeResolver)


def test_field__get_resolver__function() -> None:
    class MyQueryType(QueryType[Task]):
        @Field
        def custom(self) -> list[str]:
            return []

    resolver = MyQueryType.custom.get_resolver()
    assert isinstance(resolver, FieldFunctionResolver)


def test_field__resolve() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

        @name.resolve
        def resolve_name(self) -> str:
            return "foo"

    resolver = MyQueryType.name.get_resolver()

    assert isinstance(resolver, FieldFunctionResolver)
    assert resolver.func == MyQueryType.name.resolver_func

    assert resolver(root=None, info=mock_gql_info()) == "foo"


def test_field__resolve__parenthesis() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

        @name.resolve()
        def resolve_name(self) -> str:
            return "foo"

    resolver = MyQueryType.name.get_resolver()

    assert isinstance(resolver, FieldFunctionResolver)
    assert resolver.func == MyQueryType.name.resolver_func

    assert resolver(root=None, info=mock_gql_info()) == "foo"


def test_field__optimize() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

        @name.optimize
        def optimize_name(self, data: OptimizationData, info: GQLInfo) -> None:
            data.only_fields.add("foo")

    info = mock_gql_info()
    opt_data = OptimizationData(model=Task, info=info)

    func: OptimizerFunc = MyQueryType.name.optimizer_func  # type: ignore[assignment]

    func(MyQueryType.name, opt_data, info)

    assert opt_data.only_fields == {"foo"}


def test_field__optimize__parenthesis() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

        @name.optimize()
        def optimize_name(self, data: OptimizationData, info: GQLInfo) -> None:
            data.only_fields.add("foo")

    info = mock_gql_info()
    opt_data = OptimizationData(model=Task, info=info)

    func: OptimizerFunc = MyQueryType.name.optimizer_func  # type: ignore[assignment]

    func(MyQueryType.name, opt_data, info)

    assert opt_data.only_fields == {"foo"}


def test_field__permissions() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    task = TaskFactory.build(name="Test task")

    func = MyQueryType.name.permissions_func  # type: ignore[assignment]

    with pytest.raises(GraphQLPermissionError):
        func(MyQueryType.name, mock_gql_info(), task)


def test_field__permissions__parenthesis() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field()

        @name.permissions()
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    task = TaskFactory.build(name="Test task")

    func = MyQueryType.name.permissions_func  # type: ignore[assignment]

    with pytest.raises(GraphQLPermissionError):
        func(MyQueryType.name, mock_gql_info(), task)


def test_field__many() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field(many=True)

    assert MyQueryType.name.many is True

    field_type = MyQueryType.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


def test_field__nullable() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field(nullable=True)

    field = MyQueryType.name
    assert field.nullable is True

    field_type = field.get_field_type()
    assert field_type == GraphQLString


def test_field__nullable_and_many() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field(nullable=True, many=True)

    field = MyQueryType.name
    assert field.nullable is True
    assert field.many is True

    field_type = field.get_field_type()
    assert field_type == GraphQLList(GraphQLNonNull(GraphQLString))


def test_field__description() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field(description="Description.")

    field = MyQueryType.name
    assert field.description == "Description."

    graphql_field = field.as_graphql_field()
    assert graphql_field.description == "Description."


def test_field__description__variable_docstring(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    class MyQueryType(QueryType[Task]):
        name = Field()
        """Description."""

    field = MyQueryType.name
    assert field.description == "Description."

    graphql_field = field.as_graphql_field()
    assert graphql_field.description == "Description."


def test_field__deprecation_reason() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field(deprecation_reason="Use something else.")

    field = MyQueryType.name
    assert field.deprecation_reason == "Use something else."

    graphql_field = field.as_graphql_field()
    assert graphql_field.deprecation_reason == "Use something else."


def test_field__schema_name() -> None:
    class MyQueryType(QueryType[Task]):
        @Field(schema_name="if")
        def if_(self) -> str:
            return "if"

    assert MyQueryType.if_.schema_name == "if"


def test_field__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value=1)]

    class MyQueryType(QueryType[Task]):
        name = Field(directives=directives)

    assert MyQueryType.name.directives == directives

    assert str(MyQueryType.name) == 'name: String! @value(value: "1")'


def test_field__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.OBJECT], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    with pytest.raises(DirectiveLocationError):

        class MyQueryType(QueryType[Task]):
            name = Field(directives=[ValueDirective(value=1)])

    # Model not cleaned up since error occurred in QueryType class body.
    QueryTypeMeta.__model__ = Task


def test_field__directives__matmul() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class MyQueryType(QueryType[Task]):
        name = Field() @ ValueDirective(value="1")

    assert MyQueryType.name.directives == [ValueDirective(value="1")]

    assert str(MyQueryType.name) == 'name: String! @value(value: "1")'


def test_field__extensions() -> None:
    class MyQueryType(QueryType[Task]):
        name = Field(extensions={"foo": "bar"})

    field = MyQueryType.name
    assert field.extensions == {"foo": "bar", "undine_field": field}

    graphql_field = field.as_graphql_field()
    assert graphql_field.extensions == {"foo": "bar", "undine_field": field}


def test_field__expression_field__count() -> None:
    class MyQueryType(QueryType[Task]):
        count = Field(Count("*"))

    field = MyQueryType.count
    assert field.optimizer_func is not None

    field_type = field.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLInt)


def test_field__expression_field__upper() -> None:
    class MyQueryType(QueryType[Task]):
        upper_name = Field(Upper("name"))

    field = MyQueryType.upper_name
    assert field.optimizer_func is not None

    field_type = field.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLString)


def test_field__calculation_field() -> None:
    class ExampleCalculation(Calculation[int | None]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    class MyQueryType(QueryType[Task]):
        example = Field(ExampleCalculation)

    field = MyQueryType.example
    field_type = field.get_field_type()
    assert field_type == GraphQLInt
