from __future__ import annotations

import pytest
from django.db import models
from graphql import (
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLError,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
)

from undine.errors.exceptions import GraphQLCantCreateEnumError, GraphQLDuplicateTypeError
from undine.utils.graphql import (
    add_default_status_codes,
    compare_graphql_types,
    get_or_create_graphql_enum,
    get_or_create_input_object_type,
    get_or_create_object_type,
    maybe_list_or_non_null,
)


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    USER = "user", "User"


def test_maybe_list_or_non_null():
    field = maybe_list_or_non_null(GraphQLString, many=False, required=False)
    assert field == GraphQLString


def test_maybe_list_or_non_null__required():
    field = maybe_list_or_non_null(GraphQLString, many=False, required=True)
    assert field == GraphQLNonNull(GraphQLString)


def test_maybe_list_or_non_null__many():
    field = maybe_list_or_non_null(GraphQLString, many=True, required=False)
    assert field == GraphQLList(GraphQLNonNull(GraphQLString))


def test_maybe_list_or_non_null__many_and_required():
    field = maybe_list_or_non_null(GraphQLString, many=True, required=True)
    assert field == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


def test_add_default_status_codes():
    errors = [
        GraphQLError(message="foo"),
        GraphQLError(message="bar", extensions={"status_code": 500}),
    ]

    assert add_default_status_codes(errors) == [
        GraphQLError(message="foo", extensions={"status_code": 400}),
        GraphQLError(message="bar", extensions={"status_code": 500}),
    ]


def test_compare_graphql_types__enum__same():
    enum_1 = GraphQLEnumType(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )
    enum_2 = GraphQLEnumType(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )

    compare_graphql_types(new_type=enum_1, existing_type=enum_2)


def test_compare_graphql_types__enum__different_values():
    enum_1 = GraphQLEnumType(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )
    enum_2 = GraphQLEnumType(
        name="foo",
        values={"bar": GraphQLEnumValue(value="bar")},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        compare_graphql_types(new_type=enum_1, existing_type=enum_2)


def test_compare_graphql_types__object_type__same():
    object_type_1 = GraphQLObjectType(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )
    object_type_2 = GraphQLObjectType(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    compare_graphql_types(new_type=object_type_1, existing_type=object_type_2)


def test_compare_graphql_types__object_type__different_fields():
    object_type_1 = GraphQLObjectType(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )
    object_type_2 = GraphQLObjectType(
        name="foo",
        fields={"bar": GraphQLField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        compare_graphql_types(new_type=object_type_1, existing_type=object_type_2)


def test_compare_graphql_types__input_object_type__same():
    input_object_type_1 = GraphQLInputObjectType(
        name="foo",
        fields={"foo": GraphQLInputField(GraphQLString)},
    )
    input_object_type_2 = GraphQLInputObjectType(
        name="foo",
        fields={"foo": GraphQLInputField(GraphQLString)},
    )

    compare_graphql_types(new_type=input_object_type_1, existing_type=input_object_type_2)


def test_compare_graphql_types__input_object_type__different_fields():
    input_object_type_1 = GraphQLInputObjectType(
        name="foo",
        fields={"foo": GraphQLInputField(GraphQLString)},
    )
    input_object_type_2 = GraphQLInputObjectType(
        name="foo",
        fields={"bar": GraphQLInputField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        compare_graphql_types(new_type=input_object_type_1, existing_type=input_object_type_2)


def test_compare_graphql_types__enum_vs_object_type():
    enum = GraphQLEnumType(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )
    object_type = GraphQLObjectType(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        compare_graphql_types(new_type=enum, existing_type=object_type)


def test_compare_graphql_types__enum_vs_input_object_type():
    enum = GraphQLEnumType(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )
    input_object_type = GraphQLInputObjectType(
        name="foo",
        fields={"foo": GraphQLInputField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        compare_graphql_types(new_type=enum, existing_type=input_object_type)


def test_compare_graphql_types__object_type_vs_input_object_type():
    object_type = GraphQLObjectType(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )
    input_object_type = GraphQLInputObjectType(
        name="foo",
        fields={"foo": GraphQLInputField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        compare_graphql_types(new_type=object_type, existing_type=input_object_type)


def test_get_or_create_graphql_enum():
    enum = get_or_create_graphql_enum(name="Role", values=dict(Role.choices), description="Role of the user.")

    assert enum.name == "Role"
    assert enum.values == {
        "admin": GraphQLEnumValue(value="admin", description="Admin"),
        "user": GraphQLEnumValue(value="user", description="User"),
    }
    assert enum.description == "Role of the user."


def test_get_or_create_graphql_enum__get_same():
    enum = get_or_create_graphql_enum(name="Role", values=dict(Role.choices))
    assert get_or_create_graphql_enum(name="Role", values=dict(Role.choices)) == enum


def test_get_or_create_graphql_enum__duplicate():
    get_or_create_graphql_enum(name="Role", values=dict(Role.choices))

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_enum(name="Role", values={"foo": "Foo"})


def test_get_or_create_graphql_enum__no_choices():
    with pytest.raises(GraphQLCantCreateEnumError):
        get_or_create_graphql_enum(name="Role", values={})


def test_get_or_create_object_type():
    fields = {"foo": GraphQLField(GraphQLString)}
    obj = get_or_create_object_type(name="Object", fields=fields, description="Description.")

    assert obj.name == "Object"
    assert obj.fields == {
        "foo": GraphQLField(GraphQLString),
    }
    assert obj.description == "Description."


def test_get_or_create_object_type__get_same():
    obj = get_or_create_object_type(name="Object", fields={"foo": GraphQLField(GraphQLString)})
    assert get_or_create_object_type(name="Object", fields={"foo": GraphQLField(GraphQLString)}) == obj


def test_get_or_create_object_type__duplicate():
    get_or_create_object_type(name="Object", fields={"foo": GraphQLField(GraphQLString)})

    with pytest.raises(GraphQLDuplicateTypeError):
        assert get_or_create_object_type(name="Object", fields={"bar": GraphQLField(GraphQLString)})


def test_get_or_create_input_object_type():
    fields = {"foo": GraphQLInputField(GraphQLString)}
    obj = get_or_create_input_object_type(name="InputObject", fields=fields, description="Description.")

    assert obj.name == "InputObject"
    assert obj.fields == {
        "foo": GraphQLInputField(GraphQLString),
    }
    assert obj.description == "Description."


def test_get_or_create_input_object_type__get_same():
    obj = get_or_create_input_object_type(name="Object", fields={"foo": GraphQLInputField(GraphQLString)})
    assert get_or_create_input_object_type(name="Object", fields={"foo": GraphQLInputField(GraphQLString)}) == obj


def test_get_or_create_input_object_type__duplicate():
    get_or_create_input_object_type(name="Object", fields={"foo": GraphQLInputField(GraphQLString)})

    with pytest.raises(GraphQLDuplicateTypeError):
        assert get_or_create_input_object_type(name="Object", fields={"bar": GraphQLInputField(GraphQLString)})
