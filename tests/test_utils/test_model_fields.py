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


class MyTextChoicesFieldModel(Model):  # noqa: DJ008
    role: Role | None = TextChoicesField(choices_enum=Role, null=True)

    class Meta:
        managed = False
        app_label = __name__


FIELD = MyTextChoicesFieldModel._meta.get_field("role")


def test_text_choices_field():
    assert FIELD.choices_enum == Role
    assert FIELD.choices == [("admin", "Admin"), ("user", "User")]
    assert FIELD.max_length == 5


def test_text_choices_field__deconstruct():
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


def test_text_choices_field__to_python():
    assert FIELD.to_python("admin") == Role.ADMIN
    assert FIELD.to_python("user") == Role.USER


def test_text_choices_field__to_python__invalid():
    msg = """["`foo` is not a member of the `Role` enum. Choices are: ['admin', 'user']."]"""

    with pytest.raises(ValidationError, match=exact(msg)):
        FIELD.to_python("foo")


def test_text_choices_field__to_python__null():
    assert FIELD.to_python(None) is None


def test_text_choices_field__to_python_null__not_allowed():
    field = deepcopy(FIELD)
    field.null = False

    msg = "['This field cannot be null.']"

    with pytest.raises(ValidationError, match=exact(msg)):
        assert field.to_python(None) is None


def test_text_choices_field__from_db_value():
    assert FIELD.from_db_value("admin", ..., ...) == Role.ADMIN
    assert FIELD.from_db_value("user", ..., ...) == Role.USER


def test_text_choices_field__from_db_value__invalid():
    msg = """["`foo` is not a member of the `Role` enum. Choices are: ['admin', 'user']."]"""

    with pytest.raises(ValidationError, match=exact(msg)):
        FIELD.from_db_value("foo", ..., ...)


def test_text_choices_field__from_db_value__null():
    assert FIELD.from_db_value(None, ..., ...) is None


def test_text_choices_field__from_db_value__null__not_allowed():
    field = deepcopy(FIELD)
    field.null = False

    msg = "['This field cannot be null.']"

    with pytest.raises(ValidationError, match=exact(msg)):
        assert field.from_db_value(None, ..., ...) is None
