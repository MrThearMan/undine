from graphql import GraphQLList, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from undine import Input, MutationType


def test_input__simple():
    class MyMutationType(MutationType, model=Task):
        name = Input()

    inpt = MyMutationType.name

    assert repr(inpt) == "<undine.mutation.Input(ref=app.Task.name)>"

    assert inpt.ref == Task.name.field  # type: ignore[attr-defined]
    assert inpt.many is False
    assert inpt.required is False
    assert inpt.description is None
    assert inpt.deprecation_reason is None
    assert inpt.extensions == {"undine_input": inpt}

    assert inpt.owner == MyMutationType
    assert inpt.name == "name"

    field_type = inpt.get_field_type()
    assert field_type == GraphQLString

    graphql_input_field = inpt.as_graphql_input_field()
    assert graphql_input_field.type == field_type
    assert graphql_input_field.description is None
    assert graphql_input_field.deprecation_reason is None
    assert graphql_input_field.extensions == {"undine_input": inpt}


def test_input__many():
    class MyMutationType(MutationType, model=Task):
        name = Input(many=True)

    inpt = MyMutationType.name

    assert inpt.many is True

    field_type = inpt.get_field_type()
    assert isinstance(field_type, GraphQLList)
    assert isinstance(field_type.of_type, GraphQLNonNull)
    assert field_type.of_type.of_type == GraphQLString


def test_input__required():
    class MyMutationType(MutationType, model=Task):
        name = Input(required=True)

    inpt = MyMutationType.name

    assert inpt.required is True

    field_type = inpt.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert field_type.of_type == GraphQLString


def test_input__required_and_many():
    class MyMutationType(MutationType, model=Task):
        name = Input(required=True, many=True)

    inpt = MyMutationType.name

    assert inpt.required is True
    assert inpt.many is True

    field_type = inpt.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLList)
    assert isinstance(field_type.of_type.of_type, GraphQLNonNull)
    assert field_type.of_type.of_type.of_type == GraphQLString


def test_input__input_only():
    class MyMutationType(MutationType, model=Task):
        name = Input(input_only=True)

    inpt = MyMutationType.name

    assert inpt.input_only is True


def test_input__description():
    class MyMutationType(MutationType, model=Task):
        name = Input(description="Description.")

    inpt = MyMutationType.name

    assert inpt.description == "Description."

    graphql_input_field = inpt.as_graphql_input_field()
    assert graphql_input_field.description == "Description."


def test_input__deprecation_reason():
    class MyMutationType(MutationType, model=Task):
        name = Input(deprecation_reason="Use something else.")

    inpt = MyMutationType.name

    assert inpt.deprecation_reason == "Use something else."

    graphql_input_field = inpt.as_graphql_input_field()
    assert graphql_input_field.deprecation_reason == "Use something else."


def test_input__extensions():
    class MyMutationType(MutationType, model=Task):
        name = Input(extensions={"foo": "bar"})

    inpt = MyMutationType.name

    assert inpt.extensions == {"foo": "bar", "undine_input": inpt}

    graphql_input_field = inpt.as_graphql_input_field()
    assert graphql_input_field.extensions == {"foo": "bar", "undine_input": inpt}


# TODO: validators
