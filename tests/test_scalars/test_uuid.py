import uuid

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.uuid import parse_uuid, serialize


def test_scalar__uuid__parse__uuid():
    uuid_ = uuid.uuid4()
    assert parse_uuid(uuid_) == uuid_


def test_scalar__uuid__parse__str():
    uuid_ = uuid.uuid4()
    assert parse_uuid(str(uuid_)) == uuid_


def test_scalar__uuid__parse__bytes():
    uuid_ = uuid.uuid4()
    assert parse_uuid(uuid_.bytes) == uuid_


def test_scalar__uuid__parse__int():
    uuid_ = uuid.uuid4()
    assert parse_uuid(uuid_.int) == uuid_


@pytest.mark.parametrize("func", [parse_uuid, serialize])
def test_scalar__uuid__parse__conversion_error(func):
    msg = "UUID cannot represent value 'hello world': badly formed hexadecimal UUID string"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_uuid, serialize])
def test_scalar__uuid__parse__unsupported_type(func):
    msg = "UUID cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__uuid__serialize__uuid():
    uuid_ = uuid.uuid4()
    assert serialize(uuid_) == str(uuid_)


def test_scalar__uuid__serialize__str():
    uuid_ = uuid.uuid4()
    assert serialize(str(uuid_)) == str(uuid_)


def test_scalar__uuid__serialize__bytes():
    uuid_ = uuid.uuid4()
    assert serialize(uuid_.bytes) == str(uuid_)


def test_scalar__uuid__serialize__int():
    uuid_ = uuid.uuid4()
    assert serialize(uuid_.int) == str(uuid_)
