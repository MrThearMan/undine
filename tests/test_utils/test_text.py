import re

import pytest
from hypothesis import given, strategies

from tests.helpers import override_undine_settings
from undine.utils import comma_sep_str, to_camel_case, to_pascal_case, to_snake_case
from undine.utils.text import ALLOWED_NAME, dotpath, get_docstring


@given(strategies.from_regex(ALLOWED_NAME))
def test_to_camel_case_and_back(value: str):
    assert to_snake_case(to_camel_case(value)) == value


@given(strategies.from_regex(ALLOWED_NAME))
def test_to_pascal_case_and_back(value: str):
    n = to_pascal_case(value)
    n = n[0].lower() + n[1:]  # Convert first letter to lowercase, then we can use `to_snake_case`.
    assert to_snake_case(n) == value


@override_undine_settings(VALIDATE_NAMES_REVERSABLE=False)
@given(strategies.from_regex(re.compile(r"^[a-z][a-zA-Z0-9]*$")))
def test_camel_case_still_camel_case(value: str):
    assert to_camel_case(value) == value


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


def test_dotpath():
    class Foo: ...

    assert dotpath(Foo) == "tests.test_utils.test_text.test_dotpath.<locals>.Foo"


def test_get_docstring():
    class Foo:
        """Foo docstring"""

    assert get_docstring(Foo) == "Foo docstring"
