from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.email import email_scalar


@pytest.mark.parametrize("func", [email_scalar.parse, email_scalar.serialize])
def test_scalar__email__unsupported_type(func) -> None:
    msg = "'Email' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


@pytest.mark.parametrize("func", [email_scalar.parse, email_scalar.serialize])
def test_scalar__email__str(func) -> None:
    assert func("example@email.com") == "example@email.com"


@pytest.mark.parametrize("func", [email_scalar.parse, email_scalar.serialize])
def test_scalar__email__str__validation_error(func) -> None:
    msg = "'Email' cannot represent value 'hello world': Enter a valid email address."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [email_scalar.parse, email_scalar.serialize])
def test_scalar__email__str__empty(func) -> None:
    assert func("") == ""
