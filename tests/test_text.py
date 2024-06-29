import re

from hypothesis import given, strategies

from undine.utils.text import ALLOWED_NAME, camel_case_to_name, name_to_camel_case


@given(strategies.from_regex(ALLOWED_NAME))
def test_name_camel_case_conversion(value: str):
    assert camel_case_to_name(name_to_camel_case(value)) == value


@given(strategies.from_regex(re.compile(r"^[a-z][a-zA-Z0-9]*$")))
def test_camel_case_still_camel_case(value: str):
    assert name_to_camel_case(value, validate_reversable=False) == value
