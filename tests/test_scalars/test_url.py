from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.url import url_scalar


@pytest.mark.parametrize("func", [url_scalar.parse, url_scalar.serialize])
def test_scalar__url__unsupported_type(func) -> None:
    msg = "'URL' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


@pytest.mark.parametrize("func", [url_scalar.parse, url_scalar.serialize])
def test_scalar__url__str(func) -> None:
    assert func("https://example.com/hello") == "https://example.com/hello"


@pytest.mark.parametrize("func", [url_scalar.parse, url_scalar.serialize])
def test_scalar__url__str__validation_error(func) -> None:
    msg = "'URL' cannot represent value 'hello world': Enter a valid URL."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [url_scalar.parse, url_scalar.serialize])
def test_scalar__url__str__empty(func) -> None:
    assert func("") == ""
