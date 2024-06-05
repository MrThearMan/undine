from __future__ import annotations

import pytest
from django.db.models import TextChoices
from graphql import (
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLString,
    GraphQLUnionType,
)

from undine.exceptions import GraphQLDuplicateTypeError
from undine.utils.graphql.type_registry import (
    get_or_create_graphql_enum,
    get_or_create_graphql_input_object_type,
    get_or_create_graphql_interface_type,
    get_or_create_graphql_object_type,
    get_or_create_graphql_scalar,
    get_or_create_graphql_union,
)


class Role(TextChoices):
    ADMIN = "admin", "Admin"
    USER = "user", "User"


def test_undine_extensions__get_or_create_graphql_enum__same() -> None:
    enum_1 = get_or_create_graphql_enum(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )
    enum_2 = get_or_create_graphql_enum(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )

    assert isinstance(enum_1, GraphQLEnumType)
    assert enum_1 == enum_2


def test_undine_extensions__get_or_create_graphql_enum__different_values() -> None:
    get_or_create_graphql_enum(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_enum(
            name="foo",
            values={"bar": GraphQLEnumValue(value="bar")},
        )


def test_undine_extensions__get_or_create_graphql_enum__different_graphql_entity() -> None:
    get_or_create_graphql_object_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_enum(
            name="foo",
            values={"foo": GraphQLEnumValue(value="foo")},
        )


def test_undine_extensions__get_or_create_graphql_object_type__same() -> None:
    object_type_1 = get_or_create_graphql_object_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )
    object_type_2 = get_or_create_graphql_object_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    assert isinstance(object_type_1, GraphQLObjectType)
    assert object_type_1 == object_type_2


def test_undine_extensions__get_or_create_graphql_object_type__different_fields() -> None:
    get_or_create_graphql_object_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_object_type(
            name="foo",
            fields={"bar": GraphQLField(GraphQLString)},
        )


def test_undine_extensions__get_or_create_graphql_object_type__different_graphql_entity() -> None:
    get_or_create_graphql_enum(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_object_type(
            name="foo",
            fields={"bar": GraphQLField(GraphQLString)},
        )


def test_undine_extensions__get_or_create_graphql_input_object_type__same() -> None:
    input_object_type_1 = get_or_create_graphql_input_object_type(
        name="foo",
        fields={"foo": GraphQLInputField(GraphQLString)},
    )
    input_object_type_2 = get_or_create_graphql_input_object_type(
        name="foo",
        fields={"foo": GraphQLInputField(GraphQLString)},
    )

    assert isinstance(input_object_type_1, GraphQLInputObjectType)
    assert input_object_type_1 == input_object_type_2


def test_undine_extensions__get_or_create_graphql_input_object_type__different_fields() -> None:
    get_or_create_graphql_input_object_type(
        name="foo",
        fields={"foo": GraphQLInputField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_input_object_type(
            name="foo",
            fields={"bar": GraphQLInputField(GraphQLString)},
        )


def test_undine_extensions__get_or_create_graphql_input_object_type__different_graphql_entity() -> None:
    get_or_create_graphql_enum(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_input_object_type(
            name="foo",
            fields={"bar": GraphQLInputField(GraphQLString)},
        )


def test_undine_extensions__get_or_create_graphql_interface_type__same() -> None:
    interface_type_1 = get_or_create_graphql_interface_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )
    interface_type_2 = get_or_create_graphql_interface_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    assert isinstance(interface_type_1, GraphQLInterfaceType)
    assert interface_type_1 == interface_type_2


def test_undine_extensions__get_or_create_graphql_interface_type__different_fields() -> None:
    get_or_create_graphql_interface_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_interface_type(
            name="foo",
            fields={"bar": GraphQLField(GraphQLString)},
        )


def test_undine_extensions__get_or_create_graphql_interface_type__different_graphql_entity() -> None:
    get_or_create_graphql_enum(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_interface_type(
            name="foo",
            fields={"bar": GraphQLField(GraphQLString)},
        )


def test_undine_extensions__get_or_create_graphql_union__same() -> None:
    object_type = get_or_create_graphql_object_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    union_1 = get_or_create_graphql_union(
        name="bar",
        types=[object_type],
    )
    union_2 = get_or_create_graphql_union(
        name="bar",
        types=[object_type],
    )

    assert isinstance(union_1, GraphQLUnionType)
    assert union_1 == union_2


def test_undine_extensions__get_or_create_graphql_union__different_types() -> None:
    object_type_1 = get_or_create_graphql_object_type(
        name="foo",
        fields={"foo": GraphQLField(GraphQLString)},
    )
    object_type_2 = get_or_create_graphql_object_type(
        name="bar",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    get_or_create_graphql_union(
        name="baz",
        types=[object_type_1],
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_union(
            name="baz",
            types=[object_type_2],
        )


def test_undine_extensions__get_or_create_graphql_union__different_graphql_entity() -> None:
    get_or_create_graphql_enum(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )

    object_type = get_or_create_graphql_object_type(
        name="bar",
        fields={"foo": GraphQLField(GraphQLString)},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_union(
            name="foo",
            types=[object_type],
        )


def test_undine_extensions__get_or_create_graphql_scalar__same() -> None:
    scalar_1 = get_or_create_graphql_scalar(name="foo")
    scalar_2 = get_or_create_graphql_scalar(name="foo")

    assert isinstance(scalar_1, GraphQLScalarType)
    assert scalar_1 == scalar_2


def test_undine_extensions__get_or_create_graphql_scalar__different_specified_by_url() -> None:
    get_or_create_graphql_scalar(name="foo", specified_by_url="foo")

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_scalar(name="foo", specified_by_url="bar")


def test_undine_extensions__get_or_create_graphql_scalar__different_graphql_entity() -> None:
    get_or_create_graphql_enum(
        name="foo",
        values={"foo": GraphQLEnumValue(value="foo")},
    )

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_scalar(name="foo", specified_by_url="bar")
