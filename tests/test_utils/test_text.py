import re

import pytest
from hypothesis import given, strategies

from undine.errors.exceptions import SchemaNameValidationError
from undine.utils.text import (
    ALLOWED_NAME,
    comma_sep_str,
    dotpath,
    get_docstring,
    to_camel_case,
    to_pascal_case,
    to_snake_case,
    validate_name,
)


@given(strategies.from_regex(ALLOWED_NAME))
def test_to_camel_case_and_back(value: str):
    assert to_snake_case(to_camel_case(value)) == value


@given(strategies.from_regex(ALLOWED_NAME))
def test_to_pascal_case_and_back(value: str):
    n = to_pascal_case(value)
    n = n[0].lower() + n[1:]  # Convert first letter to lowercase, then we can use `to_snake_case`.
    assert to_snake_case(n) == value


@given(strategies.from_regex(re.compile(r"^[a-z][a-zA-Z0-9]*$")))
def test_camel_case_still_camel_case(value: str):
    assert to_camel_case(value, validate=False) == value


@pytest.mark.parametrize(
    ("values", "result"),
    [
        (["foo", "bar", "baz"], "foo, bar & baz"),
        (["foo", "bar"], "foo & bar"),
        (["foo"], "foo"),
        ([""], ""),
        (["", "foo"], "foo"),
        (["foo", ""], "foo"),
        (["", "foo", ""], "foo"),
        ([], ""),
        ([1, 2, 3], "1, 2 & 3"),
        ((i for i in ["foo", "bar", "baz"]), "foo, bar & baz"),
    ],
)
def test_comma_sep_str(values, result):
    assert comma_sep_str(values) == result


class Example: ...


def test_dotpath():
    class Foo: ...

    assert dotpath(Foo) == "tests.test_utils.test_text.test_dotpath.<locals>.Foo"
    assert dotpath(Example) == "tests.test_utils.test_text.Example"


def test_get_docstring():
    class Foo:
        """Foo docstring"""

    assert get_docstring(Foo) == "Foo docstring"


def test_validate_name():
    assert validate_name("foo") == "foo"
    assert validate_name("foo_bar") == "foo_bar"


def test_validate_name__raises():
    with pytest.raises(SchemaNameValidationError):
        validate_name("foo-bar")
