import re

import pytest

from undine.errors import GraphQLConversionError
from undine.scalars.email import parse_email


def test_scalar__email__parse__str():
    assert parse_email("example@email.com") == "example@email.com"


def test_scalar__email__parse__conversion_error():
    msg = "Email cannot represent value 'hello world': Enter a valid email address."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_email("hello world")


def test_scalar__email__parse__unsupported_type():
    msg = "Email cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_email(1.2)
