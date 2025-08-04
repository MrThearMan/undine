from __future__ import annotations

from copy import deepcopy

import pytest
from django.core.exceptions import ValidationError
from django.db.models import Model, TextChoices

from tests.helpers import exact
from undine.utils.model_fields import TextChoicesField


class Role(TextChoices):
    ADMIN = "admin", "Admin"
    USER = "user", "User"


class MyTextChoicesFieldModel(Model):
    role: Role | None = TextChoicesField(choices_enum=Role, null=True)

    class Meta:
        managed = False
        app_label = __name__


FIELD: TextChoicesField = MyTextChoicesFieldModel._meta.get_field("role")


def test_text_choices_field() -> None:
    assert FIELD.choices_enum == Role
    assert FIELD.choices == [("admin", "Admin"), ("user", "User")]
    assert FIELD.max_length == 5


def test_text_choices_field__deconstruct() -> None:
    assert FIELD.deconstruct() == (
        "role",
        "undine.utils.model_fields.TextChoicesField",
        [],
        {
            "choices": [("admin", "Admin"), ("user", "User")],
            "choices_enum": Role,
            "max_length": 5,
            "null": True,
        },
    )


def test_text_choices_field__to_python() -> None:
    assert FIELD.to_python("admin") == Role.ADMIN
    assert FIELD.to_python("user") == Role.USER


def test_text_choices_field__to_python__invalid() -> None:
    msg = {"role": ["`foo` is not a member of the `Role` enum. Choices are: 'admin' and 'user'."]}

    with pytest.raises(ValidationError, match=exact(str(msg))):
        FIELD.to_python("foo")


def test_text_choices_field__to_python__null() -> None:
    assert FIELD.to_python(None) is None


def test_text_choices_field__to_python_null__not_nullable() -> None:
    field = deepcopy(FIELD)
    field.null = False

    assert field.to_python(None) is None

    msg = ["This field cannot be null."]
    with pytest.raises(ValidationError, match=exact(str(msg))):
        field.validate(None, None)


def test_text_choices_field__from_db_value() -> None:
    assert FIELD.from_db_value("admin", ..., ...) == Role.ADMIN
    assert FIELD.from_db_value("user", ..., ...) == Role.USER


def test_text_choices_field__from_db_value__invalid() -> None:
    msg = {"role": ["`foo` is not a member of the `Role` enum. Choices are: 'admin' and 'user'."]}

    with pytest.raises(ValidationError, match=exact(str(msg))):
        FIELD.from_db_value("foo", ..., ...)


def test_text_choices_field__from_db_value__null() -> None:
    assert FIELD.from_db_value(None, ..., ...) is None


def test_text_choices_field__from_db_value__null__not_nullable() -> None:
    field = deepcopy(FIELD)
    field.null = False

    assert field.from_db_value(None, ..., ...) is None

    msg = ["This field cannot be null."]
    with pytest.raises(ValidationError, match=exact(str(msg))):
        field.validate(None, None)
