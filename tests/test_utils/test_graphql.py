from __future__ import annotations

import pytest
from django.db import models
from graphql import GraphQLEnumValue, GraphQLError, GraphQLList, GraphQLNonNull, GraphQLString

from undine.errors.exceptions import GraphQLCantCreateEnumError, GraphQLDuplicateTypeError
from undine.utils.graphql import add_default_status_codes, get_or_create_graphql_enum, maybe_list_or_non_null


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    USER = "user", "User"


def test_create_graphql_enum():
    enum = get_or_create_graphql_enum(values=dict(Role.choices), name="Role", description="Role of the user.")

    assert enum.name == "Role"
    assert enum.values == {
        "admin": GraphQLEnumValue(value="admin", description="Admin"),
        "user": GraphQLEnumValue(value="user", description="User"),
    }
    assert enum.description == "Role of the user."


def test_create_graphql_enum__get_same():
    enum = get_or_create_graphql_enum(values=dict(Role.choices), name="Role")
    assert get_or_create_graphql_enum(values=dict(Role.choices), name="Role") == enum


def test_create_graphql_enum__duplicate():
    get_or_create_graphql_enum(values=dict(Role.choices), name="Role")

    with pytest.raises(GraphQLDuplicateTypeError):
        get_or_create_graphql_enum(values={"foo": "Foo"}, name="Role")


def test_create_graphql_enum__no_choices():
    with pytest.raises(GraphQLCantCreateEnumError):
        get_or_create_graphql_enum(values={}, name="Role")


def test_maybe_list_or_non_null():
    field = maybe_list_or_non_null(GraphQLString, many=False, required=False)
    assert field == GraphQLString


def test_maybe_list_or_non_null__required():
    field = maybe_list_or_non_null(GraphQLString, many=False, required=True)
    assert isinstance(field, GraphQLNonNull)
    assert field.of_type == GraphQLString


def test_maybe_list_or_non_null__many():
    field = maybe_list_or_non_null(GraphQLString, many=True, required=False)
    assert isinstance(field, GraphQLList)
    assert isinstance(field.of_type, GraphQLNonNull)
    assert field.of_type.of_type == GraphQLString


def test_maybe_list_or_non_null__many_and_required():
    field = maybe_list_or_non_null(GraphQLString, many=True, required=True)
    assert isinstance(field, GraphQLNonNull)
    assert isinstance(field.of_type, GraphQLList)
    assert isinstance(field.of_type.of_type, GraphQLNonNull)
    assert field.of_type.of_type.of_type == GraphQLString


def test_add_default_status_codes():
    errors = [
        GraphQLError(message="foo"),
        GraphQLError(message="bar", extensions={"status_code": 500}),
    ]

    assert add_default_status_codes(errors) == [
        GraphQLError(message="foo", extensions={"status_code": 400}),
        GraphQLError(message="bar", extensions={"status_code": 500}),
    ]
