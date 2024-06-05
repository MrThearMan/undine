from __future__ import annotations

from graphql import DirectiveLocation

from undine.directives import Directive
from undine.scalars import ScalarType


def test_scalar__scalar_type__repr() -> None:
    my_scalar: ScalarType[str, str] = ScalarType(name="MyScalar")

    assert repr(my_scalar) == "<undine.scalars._definition.ScalarType(name='MyScalar')>"


def test_scalar__scalar_type__str() -> None:
    my_scalar: ScalarType[str, str] = ScalarType(name="MyScalar")

    assert str(my_scalar) == "scalar MyScalar"


def test_scalar__scalar_type__str__specified_by_url() -> None:
    my_scalar: ScalarType[str, str] = ScalarType(name="MyScalar", specified_by_url="www.example.com")

    assert str(my_scalar) == 'scalar MyScalar @specifiedBy(url: "www.example.com")'


def test_scalar__scalar_type__str__custom_directive() -> None:
    class CustomDirective(Directive, locations=[DirectiveLocation.SCALAR], schema_name="custom"): ...

    my_scalar: ScalarType[str, str] = ScalarType(name="MyScalar", directives=[CustomDirective()])

    assert str(my_scalar) == "scalar MyScalar @custom"


def test_scalar__scalar_type__as_graphql_scalar() -> None:
    my_scalar: ScalarType[str, str] = ScalarType(name="MyScalar")

    scalar_type = my_scalar.as_graphql_scalar()

    assert scalar_type.name == "MyScalar"
    assert scalar_type.serialize is my_scalar.serialize
    assert scalar_type.parse_value is my_scalar.parse
    assert scalar_type.specified_by_url is None
    assert scalar_type.description is None
    assert scalar_type.extensions == {"undine_scalar": my_scalar}


def test_scalar__scalar_type__parse() -> None:
    my_scalar: ScalarType[str, str] = ScalarType(name="MyScalar")

    @my_scalar.parse.register
    def _(value: str) -> str:
        return value.upper()

    assert my_scalar.parse("foo") == "FOO"


def test_scalar__scalar_type__serialize() -> None:
    my_scalar: ScalarType[str, str] = ScalarType(name="MyScalar")

    @my_scalar.serialize.register
    def _(value: str) -> str:
        return value.upper()

    assert my_scalar.serialize("foo") == "FOO"
