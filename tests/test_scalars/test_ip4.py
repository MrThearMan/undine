from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.ipv4 import ipv4_scalar


@pytest.mark.parametrize("func", [ipv4_scalar.parse, ipv4_scalar.serialize])
def test_scalar__ip__unsupported_type(func) -> None:
    msg = "'IPv4' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


@pytest.mark.parametrize("func", [ipv4_scalar.parse, ipv4_scalar.serialize])
def test_scalar__ip__str__ipv4(func) -> None:
    assert func("127.0.0.1") == "127.0.0.1"


@pytest.mark.parametrize("func", [ipv4_scalar.parse, ipv4_scalar.serialize])
def test_scalar__ip__str__ipv6(func) -> None:
    msg = "'IPv4' cannot represent value '24f0:7229:ab2d:b112:4c1b:1c75:f4ee:9737': Enter a valid IPv4 address."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func("24f0:7229:ab2d:b112:4c1b:1c75:f4ee:9737")


@pytest.mark.parametrize("func", [ipv4_scalar.parse, ipv4_scalar.serialize])
def test_scalar__ip__str__validation_error(func) -> None:
    msg = "'IPv4' cannot represent value 'hello world': Enter a valid IPv4 address."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func("hello world")
