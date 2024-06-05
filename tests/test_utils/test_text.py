import re

import pytest
from hypothesis import given, strategies

from undine.utils.text import comma_sep_str, dotpath, get_docstring, to_camel_case, to_pascal_case, to_snake_case

# fmt: off
ALLOWED_NAME = re.compile(
    r"^"          # Start of string
    r"[a-z]"      # First character must be a letter.
    r"(?:"        # Followed by (non-capturing group):
    r"[a-z0-9]"   # 1) Any number of letters or numbers
    r"|"          # OR
    r"(_[a-z])"   # 2) An underscore followed by a letter
    r")*"         # Zero or more of the above
    r"$",         # End of string
)
# fmt: on


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


class Example: ...


def test_dotpath():
    class Foo: ...

    assert dotpath(Foo) == "tests.test_utils.test_text.test_dotpath.<locals>.Foo"
    assert dotpath(Example) == "tests.test_utils.test_text.Example"


def test_get_docstring():
    class Foo:
        """Foo docstring"""

    assert get_docstring(Foo) == "Foo docstring"
