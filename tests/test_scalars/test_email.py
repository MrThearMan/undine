import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.email import parse_email, serialize


@pytest.mark.parametrize("func", [parse_email, serialize])
def test_scalar__email__parse__str(func):
    assert func("example@email.com") == "example@email.com"


@pytest.mark.parametrize("func", [parse_email, serialize])
def test_scalar__email__parse__conversion_error(func):
    msg = "'Email' cannot represent value 'hello world': Enter a valid email address."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_email, serialize])
def test_scalar__email__parse__unsupported_type(func):
    msg = "'Email' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1.2)
