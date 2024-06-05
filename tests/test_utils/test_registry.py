from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import RegistryDuplicateError, RegistryMissingTypeError
from undine.utils.registy import Registry


def test_registry__basic() -> None:
    registry = Registry()

    registry["foo"] = "bar"
    assert registry["foo"] == "bar"


def test_registry__doesnt_exist() -> None:
    registry = Registry()

    msg = "'registry' doesn't contain an entry for 'foo'"
    with pytest.raises(RegistryMissingTypeError, match=exact(msg)):
        assert registry["foo"]


def test_registry__contains() -> None:
    registry = Registry()
    registry["foo"] = "bar"

    assert "foo" in registry
    assert "bar" not in registry


def test_registry__set_duplicate() -> None:
    registry = Registry()
    registry["foo"] = "bar"

    msg = "'registry' already contains a value for 'foo': 'bar'"
    with pytest.raises(RegistryDuplicateError, match=exact(msg)):
        registry["foo"] = "baz"


def test_registry__clear() -> None:
    registry = Registry()
    registry["foo"] = "bar"
    registry["fizz"] = "buzz"

    assert "foo" in registry
    assert "fizz" in registry

    registry.clear()

    assert "foo" not in registry
    assert "fizz" not in registry
