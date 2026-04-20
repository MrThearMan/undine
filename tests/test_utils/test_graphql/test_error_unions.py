from __future__ import annotations

import inspect
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from graphql import GraphQLError, GraphQLString

from tests.helpers import mock_gql_info
from undine.typing import ErrorUnionFieldErrorDict, ErrorUnionFieldValueDict
from undine.utils.graphql.error_unions import (
    build_union_with_errors,
    default_union_error_resolver,
    error_union_resolver_wrapper,
    resolve_field_error_message,
)


def test_resolve_field_error_message__graphql_error() -> None:
    error = GraphQLError("Something went wrong")
    assert resolve_field_error_message(error) == "Something went wrong"


def test_resolve_field_error_message__validation_error() -> None:
    error = ValidationError("Invalid value: %(val)s", params={"val": "bad"})
    assert resolve_field_error_message(error) == "Invalid value: bad"


def test_resolve_field_error_message__generic_error_with_message() -> None:
    class MyError(Exception):
        message = "My error message"

    assert resolve_field_error_message(MyError()) == "My error message"


def test_resolve_field_error_message__generic_error_no_message() -> None:
    error = ValueError("fallback str")
    assert resolve_field_error_message(error) == "fallback str"


def test_default_union_error_resolver() -> None:
    error = ValueError("test error")
    result = default_union_error_resolver(error, mock_gql_info())
    assert result == {"message": "test error"}


def test_build_union_with_errors() -> None:
    union_type = build_union_with_errors(
        name="MyFieldResult",
        field_type=GraphQLString,
        errors=[ValueError],
    )
    assert union_type is not None
    inner = union_type.of_type
    assert inner.name == "MyFieldResult"


def test_build_union_with_errors__resolve_type__value() -> None:
    union_type = build_union_with_errors(
        name="TestResult",
        field_type=GraphQLString,
        errors=[ValueError],
    )
    inner = union_type.of_type
    resolve_type = inner.resolve_type
    info = mock_gql_info()

    value_dict = ErrorUnionFieldValueDict(value="hello")
    result = resolve_type(value_dict, info, inner)
    assert result == "TestResultValue"


def test_build_union_with_errors__resolve_type__known_error() -> None:
    union_type = build_union_with_errors(
        name="TestResult2",
        field_type=GraphQLString,
        errors=[ValueError],
    )
    inner = union_type.of_type
    resolve_type = inner.resolve_type
    info = mock_gql_info()

    error_dict = ErrorUnionFieldErrorDict({}, error=ValueError("oops"))
    result = resolve_type(error_dict, info, inner)
    assert result == "ValueError"


def test_build_union_with_errors__resolve_type__unknown_error() -> None:
    union_type = build_union_with_errors(
        name="TestResult3",
        field_type=GraphQLString,
        errors=[ValueError],
    )
    inner = union_type.of_type
    resolve_type = inner.resolve_type
    info = mock_gql_info()

    error_dict = ErrorUnionFieldErrorDict({}, error=TypeError("unknown"))
    result = resolve_type(error_dict, info, inner)
    assert result is None


def test_error_union_resolver_wrapper__success() -> None:
    def resolver(root: Any, info: Any, **kwargs: Any) -> str:
        return "result"

    wrapped = error_union_resolver_wrapper(resolver, [ValueError])
    result = wrapped(None, mock_gql_info())
    assert isinstance(result, dict)
    assert result["value"] == "result"


def test_error_union_resolver_wrapper__known_error() -> None:
    def resolver(root: Any, info: Any, **kwargs: Any) -> str:
        msg = "expected error"
        raise ValueError(msg)

    wrapped = error_union_resolver_wrapper(resolver, [ValueError])
    result = wrapped(None, mock_gql_info())
    assert isinstance(result, ErrorUnionFieldErrorDict)
    assert result["message"] == "expected error"


def test_error_union_resolver_wrapper__unknown_error_reraises() -> None:
    def resolver(root: Any, info: Any, **kwargs: Any) -> str:
        msg = "unexpected"
        raise TypeError(msg)

    wrapped = error_union_resolver_wrapper(resolver, [ValueError])
    with pytest.raises(TypeError, match="unexpected"):
        wrapped(None, mock_gql_info())


@pytest.mark.asyncio
async def test_error_union_resolver_wrapper__async_success() -> None:
    async def async_resolver(root: Any, info: Any, **kwargs: Any) -> str:  # noqa: RUF029
        return "async_result"

    wrapped = error_union_resolver_wrapper(async_resolver, [ValueError])
    coro = wrapped(None, mock_gql_info(is_awaitable=inspect.isawaitable))
    result = await coro
    assert result["value"] == "async_result"


@pytest.mark.asyncio
async def test_error_union_resolver_wrapper__async_known_error() -> None:
    async def async_resolver(root: Any, info: Any, **kwargs: Any) -> str:  # noqa: RUF029
        msg = "async error"
        raise ValueError(msg)

    wrapped = error_union_resolver_wrapper(async_resolver, [ValueError])
    coro = wrapped(None, mock_gql_info(is_awaitable=inspect.isawaitable))
    result = await coro
    assert isinstance(result, ErrorUnionFieldErrorDict)
    assert result["message"] == "async error"


@pytest.mark.asyncio
async def test_error_union_resolver_wrapper__async_unknown_error_reraises() -> None:
    async def async_resolver(root: Any, info: Any, **kwargs: Any) -> str:  # noqa: RUF029
        msg = "async unexpected"
        raise TypeError(msg)

    wrapped = error_union_resolver_wrapper(async_resolver, [ValueError])
    coro = wrapped(None, mock_gql_info(is_awaitable=inspect.isawaitable))
    with pytest.raises(TypeError, match="async unexpected"):
        await coro
