from __future__ import annotations

from typing import AsyncGenerator, AsyncIterable, AsyncIterator, Self

import pytest

from tests.helpers import mock_gql_info
from undine import Entrypoint, GQLInfo, RootType
from undine.resolvers import FunctionSubscriptionResolver, SubscriptionValueResolver


@pytest.mark.parametrize("value", [None, 42, "abc"])
def test_subscription_value_resolver(value) -> None:
    resolver = SubscriptionValueResolver()

    assert resolver(value, mock_gql_info()) == value


@pytest.mark.asyncio
async def test_entrypoint_function_subscription__async_generator() -> None:
    class Subscription(RootType):
        @Entrypoint
        async def func(self, info: GQLInfo) -> AsyncGenerator[int, None]:
            for i in range(2):
                yield i

    resolver_func = Subscription.func.get_resolver()
    assert isinstance(resolver_func, SubscriptionValueResolver)

    resolver = FunctionSubscriptionResolver(func=Subscription.func.ref, entrypoint=Subscription.func)

    result = [item async for item in resolver(None, mock_gql_info())]
    assert result == [0, 1]


@pytest.mark.asyncio
async def test_entrypoint_function_subscription__async_iterator() -> None:
    class ExampleIterator:
        def __init__(self) -> None:
            self.values = list(range(2))
            self.index = 0

        def __aiter__(self) -> Self:
            return self

        async def __anext__(self) -> int:
            if self.index >= len(self.values):
                raise StopAsyncIteration
            value = self.values[self.index]
            self.index += 1
            return value

    class Subscription(RootType):
        @Entrypoint
        async def func(self, info: GQLInfo) -> AsyncIterator[int]:
            return ExampleIterator()

    resolver_func = Subscription.func.get_resolver()
    assert isinstance(resolver_func, SubscriptionValueResolver)

    resolver = FunctionSubscriptionResolver(func=Subscription.func.ref, entrypoint=Subscription.func)

    result = [item async for item in resolver(None, mock_gql_info())]
    assert result == [0, 1]


@pytest.mark.asyncio
async def test_entrypoint_function_subscription__async_iterable() -> None:
    class ExampleIterable:
        def __aiter__(self) -> AsyncIterator[int]:
            return self.gen()

        async def gen(self) -> AsyncGenerator[int, None]:
            for i in range(2):
                yield i

    class Subscription(RootType):
        @Entrypoint
        async def func(self, info: GQLInfo) -> AsyncIterable[int]:
            return ExampleIterable()

    resolver_func = Subscription.func.get_resolver()
    assert isinstance(resolver_func, SubscriptionValueResolver)

    resolver = FunctionSubscriptionResolver(func=Subscription.func.ref, entrypoint=Subscription.func)

    result = [item async for item in resolver(None, mock_gql_info())]
    assert result == [0, 1]
