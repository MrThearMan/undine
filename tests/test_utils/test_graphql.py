from __future__ import annotations

from copy import deepcopy

import pytest
from django.db import models
from graphql import GraphQLEnumValue, GraphQLError, GraphQLList, GraphQLNonNull, GraphQLString

from undine.errors.exceptions import GraphQLCantCreateEnumError, GraphQLDuplicateEnumError
from undine.utils.graphql import add_default_status_codes, create_graphql_enum, maybe_list_or_non_null


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    USER = "user", "User"


class MyCharFieldChoicesModel(models.Model):  # noqa: DJ008
    role: Role = models.CharField(
        choices=Role.choices,
        max_length=5,
        help_text="Role of the user.",
    )

    class Meta:
        managed = False
        app_label = "tests"


FIELD = MyCharFieldChoicesModel._meta.get_field("role")


def test_create_graphql_enum():
    enum = create_graphql_enum(FIELD)

    assert enum.name == "MyCharFieldChoicesModelRoleChoices"
    assert enum.values == {
        "ADMIN": GraphQLEnumValue(value="admin", description="Admin"),
        "USER": GraphQLEnumValue(value="user", description="User"),
    }
    assert enum.description == "Role of the user."


def test_create_graphql_enum__get_same():
    enum = create_graphql_enum(FIELD)
    assert create_graphql_enum(FIELD) == enum


def test_create_graphql_enum__duplicate():
    create_graphql_enum(FIELD)

    field = deepcopy(FIELD)
    field.choices = [("foo", "Foo")]

    with pytest.raises(GraphQLDuplicateEnumError):
        create_graphql_enum(field)


def test_create_graphql_enum__custom_name():
    enum = create_graphql_enum(FIELD, name="foo")
    assert enum.name == "foo"


def test_create_graphql_enum__custom_description():
    enum = create_graphql_enum(FIELD, description="foo")
    assert enum.description == "foo"


def test_create_graphql_enum__no_choices():
    field = deepcopy(FIELD)
    field.choices = None

    with pytest.raises(GraphQLCantCreateEnumError):
        create_graphql_enum(field)


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
