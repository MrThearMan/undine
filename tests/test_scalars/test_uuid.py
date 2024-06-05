from __future__ import annotations

import uuid

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.uuid import uuid_scalar


@pytest.mark.parametrize("func", [uuid_scalar.parse, uuid_scalar.serialize])
def test_scalar__uuid__unsupported_type(func) -> None:
    msg = "'UUID' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__uuid__parse__str() -> None:
    uuid_ = uuid.uuid4()
    assert uuid_scalar.parse(str(uuid_)) == uuid_


def test_scalar__uuid__parse__conversion_error() -> None:
    msg = "'UUID' cannot represent value 'hello world': badly formed hexadecimal UUID string"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        uuid_scalar.parse("hello world")


def test_scalar__uuid__parse__int() -> None:
    uuid_ = uuid.uuid4()
    assert uuid_scalar.parse(uuid_.int) == uuid_


def test_scalar__uuid__serialize__uuid() -> None:
    uuid_ = uuid.uuid4()
    assert uuid_scalar.serialize(uuid_) == str(uuid_)


def test_scalar__uuid__serialize__str() -> None:
    uuid_ = uuid.uuid4()
    assert uuid_scalar.serialize(str(uuid_)) == str(uuid_)


def test_scalar__uuid__serialize__str__conversion_error() -> None:
    msg = "'UUID' cannot represent value 'hello world': badly formed hexadecimal UUID string"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        uuid_scalar.serialize("hello world")


def test_scalar__uuid__serialize__bytes() -> None:
    uuid_ = uuid.uuid4()
    assert uuid_scalar.serialize(uuid_.bytes) == str(uuid_)


def test_scalar__uuid__serialize__int() -> None:
    uuid_ = uuid.uuid4()
    assert uuid_scalar.serialize(uuid_.int) == str(uuid_)
