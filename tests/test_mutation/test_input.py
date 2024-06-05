import pytest
from graphql import GraphQLList, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.helpers import MockGQLInfo, exact
from undine import Input, MutationType
from undine.errors.exceptions import GraphQLPermissionDeniedError
from undine.typing import GQLInfo


def test_input__repr():
    class MyMutationType(MutationType, model=Task):
        name = Input()

    assert repr(MyMutationType.name) == "<undine.mutation.Input(ref=app.Task.name)>"


def test_input__attributes():
    class MyMutationType(MutationType, model=Task):
        name = Input()

    assert MyMutationType.name.ref == Task._meta.get_field("name")
    assert MyMutationType.name.many is False
    assert MyMutationType.name.required is False
    assert MyMutationType.name.description is None
    assert MyMutationType.name.deprecation_reason is None
    assert MyMutationType.name.extensions == {"undine_input": MyMutationType.name}
    assert MyMutationType.name.mutation_type == MyMutationType
    assert MyMutationType.name.name == "name"


def test_input__get_field_type():
    class MyMutationType(MutationType, model=Task):
        name = Input()

    field_type = MyMutationType.name.get_field_type()
    assert field_type == GraphQLString


def test_input__as_graphql_input_field():
    class MyMutationType(MutationType, model=Task):
        name = Input()

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.type == GraphQLString
    assert graphql_input_field.description is None
    assert graphql_input_field.deprecation_reason is None
    assert graphql_input_field.extensions == {"undine_input": MyMutationType.name}


def test_input__many():
    class MyMutationType(MutationType, model=Task):
        name = Input(many=True)

    assert MyMutationType.name.many is True

    field_type = MyMutationType.name.get_field_type()
    assert field_type == GraphQLList(GraphQLNonNull(GraphQLString))


def test_input__required():
    class MyMutationType(MutationType, model=Task):
        name = Input(required=True)

    assert MyMutationType.name.required is True

    field_type = MyMutationType.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLString)


def test_input__required_and_many():
    class MyMutationType(MutationType, model=Task):
        name = Input(required=True, many=True)

    assert MyMutationType.name.required is True
    assert MyMutationType.name.many is True

    field_type = MyMutationType.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


def test_input__input_only():
    class MyMutationType(MutationType, model=Task):
        name = Input(input_only=True)

    assert MyMutationType.name.input_only is True


def test_input__description():
    class MyMutationType(MutationType, model=Task):
        name = Input(description="Description.")

    assert MyMutationType.name.description == "Description."

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.description == "Description."


def test_input__deprecation_reason():
    class MyMutationType(MutationType, model=Task):
        name = Input(deprecation_reason="Use something else.")

    assert MyMutationType.name.deprecation_reason == "Use something else."

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.deprecation_reason == "Use something else."


def test_input__extensions():
    class MyMutationType(MutationType, model=Task):
        name = Input(extensions={"foo": "bar"})

    assert MyMutationType.name.extensions == {"foo": "bar", "undine_input": MyMutationType.name}

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.extensions == {"foo": "bar", "undine_input": MyMutationType.name}


def test_input__validator():
    class MyMutationType(MutationType, model=Task):
        name = Input()

        @name.validate
        def validate_name(self: Input, info: GQLInfo, value: str) -> None:
            if value == "foo":
                msg = "Name must not be 'foo'"
                raise ValueError(msg)

    assert MyMutationType.name.validator_func is MyMutationType.validate_name

    with pytest.raises(ValueError, match=exact("Name must not be 'foo'")):
        MyMutationType.validate_name(MyMutationType.name, MockGQLInfo(), "foo")


def test_input__permissions():
    class MyMutationType(MutationType, model=Task):
        name = Input()

        @name.permissions
        def name_permissions(self: Input, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionDeniedError

    assert MyMutationType.name.permissions_func is MyMutationType.name_permissions

    with pytest.raises(GraphQLPermissionDeniedError):
        MyMutationType.name_permissions(MyMutationType.name, MockGQLInfo(), "foo")
