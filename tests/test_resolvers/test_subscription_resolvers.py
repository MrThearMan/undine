from __future__ import annotations

from typing import AsyncGenerator, AsyncIterable, AsyncIterator, Self
from unittest.mock import MagicMock, patch

import pytest
from graphql import GraphQLError

from example_project.app.models import Task
from tests.helpers import mock_gql_info
from undine import Entrypoint, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLErrorGroup
from undine.resolvers import FunctionSubscriptionResolver, SubscriptionValueResolver
from undine.resolvers.subscription import ModelDeleteSubscriptionResolver, ModelSaveSubscriptionResolver


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


@pytest.mark.asyncio
async def test_function_subscription_resolver__no_root_info_params() -> None:
    async def my_func() -> AsyncGenerator[int, None]:  # noqa: RUF029
        yield 42

    class Sub(RootType):
        @Entrypoint
        async def sub(self) -> AsyncGenerator[int, None]:
            yield 0

    resolver = FunctionSubscriptionResolver(func=my_func, entrypoint=Sub.sub)
    result = [item async for item in resolver(None, mock_gql_info())]

    assert result == [42]


@pytest.mark.asyncio
async def test_function_subscription_resolver__graphql_error_group_result() -> None:
    error_group = GraphQLErrorGroup(errors=[GraphQLError("inner")])

    async def my_func() -> AsyncGenerator[GraphQLErrorGroup, None]:  # noqa: RUF029
        yield error_group

    class Sub(RootType):
        @Entrypoint
        async def sub(self) -> AsyncGenerator[int, None]:
            yield 0

    resolver = FunctionSubscriptionResolver(func=my_func, entrypoint=Sub.sub)
    results = [item async for item in resolver(None, mock_gql_info())]

    assert len(results) == 1

    assert isinstance(results[0], GraphQLErrorGroup)


@pytest.mark.asyncio
async def test_function_subscription_resolver__graphql_error_result() -> None:

    error = GraphQLError("test error")

    async def my_func() -> AsyncGenerator[GraphQLError, None]:  # noqa: RUF029
        yield error

    class Sub(RootType):
        @Entrypoint
        async def sub(self) -> AsyncGenerator[int, None]:
            yield 0

    resolver = FunctionSubscriptionResolver(func=my_func, entrypoint=Sub.sub)
    results = [item async for item in resolver(None, mock_gql_info())]

    assert len(results) == 1
    assert isinstance(results[0], GraphQLError)


@pytest.mark.asyncio
async def test_function_subscription_resolver__error_group_raised() -> None:

    error_group = GraphQLErrorGroup(errors=[GraphQLError("inner")])

    async def my_func() -> AsyncGenerator[int, None]:  # noqa: RUF029
        raise error_group
        yield  # make it an async generator

    class Sub(RootType):
        @Entrypoint
        async def sub(self) -> AsyncGenerator[int, None]:
            yield 0

    resolver = FunctionSubscriptionResolver(func=my_func, entrypoint=Sub.sub)

    with pytest.raises(GraphQLErrorGroup):
        async for _ in resolver(None, mock_gql_info()):
            pass


@pytest.mark.asyncio
async def test_function_subscription_resolver__exception_raised() -> None:
    async def my_func() -> AsyncGenerator[int, None]:  # noqa: RUF029
        msg = "test error"
        raise ValueError(msg)
        yield

    class Sub(RootType):
        @Entrypoint
        async def sub(self) -> AsyncGenerator[int, None]:
            yield 0

    resolver = FunctionSubscriptionResolver(func=my_func, entrypoint=Sub.sub)

    with pytest.raises(GraphQLError):
        async for _ in resolver(None, mock_gql_info()):
            pass


@pytest.mark.asyncio
async def test_function_subscription_resolver__sync_permissions() -> None:
    permissions_called = []

    async def my_func() -> AsyncGenerator[int, None]:  # noqa: RUF029
        yield 42

    class Sub(RootType):
        @Entrypoint
        async def sub(self) -> AsyncGenerator[int, None]:
            yield 0

        @sub.permissions
        def _(root: object, info: GQLInfo, instance: int) -> None:
            permissions_called.append(instance)

    resolver = FunctionSubscriptionResolver(func=my_func, entrypoint=Sub.sub)
    results = [item async for item in resolver(None, mock_gql_info())]

    assert results == [42]
    assert permissions_called == [42]


@pytest.mark.asyncio
async def test_function_subscription_resolver__async_permissions() -> None:
    permissions_called = []

    async def my_func() -> AsyncGenerator[int, None]:  # noqa: RUF029
        yield 42

    class Sub(RootType):
        @Entrypoint
        async def sub(self) -> AsyncGenerator[int, None]:
            yield 0

        @sub.permissions
        async def _(root: object, info: GQLInfo, instance: int) -> None:
            permissions_called.append(instance)

    resolver = FunctionSubscriptionResolver(func=my_func, entrypoint=Sub.sub)
    results = [item async for item in resolver(None, mock_gql_info())]

    assert results == [42]
    assert permissions_called == [42]


@pytest.mark.asyncio
async def test_model_save_subscription_resolver() -> None:

    task = Task(name="Test task", pk=1)

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        yield task

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class TaskType(QueryType[Task]): ...

    subscription.query_type = TaskType

    class Sub(RootType):
        @Entrypoint
        async def on_save(self) -> AsyncGenerator[Task, None]:
            yield task

    async def mock_optimize_async(*args, **kwargs):  # noqa: RUF029
        return task

    with patch("undine.resolvers.subscription.optimize_async", new=mock_optimize_async):
        resolver = ModelSaveSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_save)
        results = [r async for r in resolver(None, mock_gql_info())]

    assert results == [task]


@pytest.mark.asyncio
async def test_model_save_subscription_resolver__instance_not_found() -> None:

    task = Task(name="Test task", pk=1)

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        yield task

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class TaskType(QueryType[Task]): ...

    subscription.query_type = TaskType

    class Sub(RootType):
        @Entrypoint
        async def on_save(self) -> AsyncGenerator[Task, None]:
            yield task

    async def mock_optimize_async(*args, **kwargs):  # noqa: RUF029
        return None

    with patch("undine.resolvers.subscription.optimize_async", new=mock_optimize_async):
        resolver = ModelSaveSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_save)
        results = [r async for r in resolver(None, mock_gql_info())]

    assert results == []


@pytest.mark.asyncio
async def test_model_save_subscription_resolver__sync_entrypoint_permissions() -> None:

    task = Task(name="Test task", pk=1)
    permissions_called = []

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        yield task

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class TaskType(QueryType[Task]): ...

    subscription.query_type = TaskType

    class Sub(RootType):
        @Entrypoint
        async def on_save(self) -> AsyncGenerator[Task, None]:
            yield task

        @on_save.permissions
        def _(root: object, info: GQLInfo, instance: Task) -> None:
            permissions_called.append(instance)

    async def mock_optimize_async(*args, **kwargs):  # noqa: RUF029
        return task

    with patch("undine.resolvers.subscription.optimize_async", new=mock_optimize_async):
        resolver = ModelSaveSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_save)
        results = [r async for r in resolver(None, mock_gql_info())]

    assert results == [task]
    assert permissions_called == [task]


@pytest.mark.asyncio
async def test_model_save_subscription_resolver__async_entrypoint_permissions() -> None:

    task = Task(name="Test task", pk=1)
    permissions_called = []

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        yield task

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class TaskType(QueryType[Task]): ...

    subscription.query_type = TaskType

    class Sub(RootType):
        @Entrypoint
        async def on_save(self) -> AsyncGenerator[Task, None]:
            yield task

        @on_save.permissions
        async def _(root: object, info: GQLInfo, instance: Task) -> None:
            permissions_called.append(instance)

    async def mock_optimize_async(*args, **kwargs):  # noqa: RUF029
        return task

    with patch("undine.resolvers.subscription.optimize_async", new=mock_optimize_async):
        resolver = ModelSaveSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_save)
        results = [r async for r in resolver(None, mock_gql_info())]

    assert results == [task]
    assert permissions_called == [task]


@pytest.mark.asyncio
async def test_model_save_subscription_resolver__async_query_type_permissions() -> None:

    task = Task(name="Test task", pk=1)
    permissions_called = []

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        yield task

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class TaskType(QueryType[Task]):
        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            permissions_called.append(instance)

    subscription.query_type = TaskType

    class Sub(RootType):
        @Entrypoint
        async def on_save(self) -> AsyncGenerator[Task, None]:
            yield task

    async def mock_optimize_async(*args, **kwargs):  # noqa: RUF029
        return task

    with patch("undine.resolvers.subscription.optimize_async", new=mock_optimize_async):
        resolver = ModelSaveSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_save)
        results = [r async for r in resolver(None, mock_gql_info())]

    assert results == [task]
    assert permissions_called == [task]


@pytest.mark.asyncio
async def test_model_save_subscription_resolver__error_group_raised() -> None:

    task = Task(name="Test task", pk=1)
    error_group = GraphQLErrorGroup(errors=[GraphQLError("inner")])

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        raise error_group
        yield task  # noqa: unreachable

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class TaskType(QueryType[Task]): ...

    subscription.query_type = TaskType

    class Sub(RootType):
        @Entrypoint
        async def on_save(self) -> AsyncGenerator[Task, None]:
            yield task

    async def mock_optimize_async(*args, **kwargs):  # noqa: RUF029
        return task

    with patch("undine.resolvers.subscription.optimize_async", new=mock_optimize_async):
        resolver = ModelSaveSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_save)

        with pytest.raises(GraphQLErrorGroup):
            async for _ in resolver(None, mock_gql_info()):
                pass


@pytest.mark.asyncio
async def test_model_save_subscription_resolver__exception_raised() -> None:

    task = Task(name="Test task", pk=1)

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        msg = "test error"
        raise ValueError(msg)
        yield task  # noqa: unreachable

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class TaskType(QueryType[Task]): ...

    subscription.query_type = TaskType

    class Sub(RootType):
        @Entrypoint
        async def on_save(self) -> AsyncGenerator[Task, None]:
            yield task

    async def mock_optimize_async(*args, **kwargs):  # noqa: RUF029
        return task

    with patch("undine.resolvers.subscription.optimize_async", new=mock_optimize_async):
        resolver = ModelSaveSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_save)

        with pytest.raises(GraphQLError):
            async for _ in resolver(None, mock_gql_info()):
                pass


@pytest.mark.asyncio
async def test_model_delete_subscription_resolver() -> None:

    task = Task(name="Test task", pk=1)

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        yield task

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class Sub(RootType):
        @Entrypoint
        async def on_delete(self) -> AsyncGenerator[Task, None]:
            yield task

    resolver = ModelDeleteSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_delete)
    results = [r async for r in resolver(None, mock_gql_info())]

    assert results == [task]


@pytest.mark.asyncio
async def test_model_delete_subscription_resolver__sync_entrypoint_permissions() -> None:

    task = Task(name="Test task", pk=1)
    permissions_called = []

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        yield task

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class Sub(RootType):
        @Entrypoint
        async def on_delete(self) -> AsyncGenerator[Task, None]:
            yield task

        @on_delete.permissions
        def _(root: object, info: GQLInfo, instance: Task) -> None:
            permissions_called.append(instance)

    resolver = ModelDeleteSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_delete)
    results = [r async for r in resolver(None, mock_gql_info())]

    assert results == [task]
    assert permissions_called == [task]


@pytest.mark.asyncio
async def test_model_delete_subscription_resolver__async_entrypoint_permissions() -> None:

    task = Task(name="Test task", pk=1)
    permissions_called = []

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        yield task

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class Sub(RootType):
        @Entrypoint
        async def on_delete(self) -> AsyncGenerator[Task, None]:
            yield task

        @on_delete.permissions
        async def _(root: object, info: GQLInfo, instance: Task) -> None:
            permissions_called.append(instance)

    resolver = ModelDeleteSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_delete)
    results = [r async for r in resolver(None, mock_gql_info())]

    assert results == [task]
    assert permissions_called == [task]


@pytest.mark.asyncio
async def test_model_delete_subscription_resolver__error_group_raised() -> None:
    task = Task(name="Test task", pk=1)
    error_group = GraphQLErrorGroup(errors=[GraphQLError("inner")])

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        raise error_group
        yield task  # noqa: unreachable

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class Sub(RootType):
        @Entrypoint
        async def on_delete(self) -> AsyncGenerator[Task, None]:
            yield task

    resolver = ModelDeleteSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_delete)

    with pytest.raises(GraphQLErrorGroup):
        async for _ in resolver(None, mock_gql_info()):
            pass


@pytest.mark.asyncio
async def test_model_delete_subscription_resolver__exception_raised() -> None:

    task = Task(name="Test task", pk=1)

    async def fake_event_stream() -> AsyncGenerator[Task, None]:  # noqa: RUF029
        msg = "test error"
        raise ValueError(msg)
        yield task  # noqa: unreachable

    subscriber = MagicMock()
    subscriber.subscribe = fake_event_stream

    subscription = MagicMock()
    subscription.create_subscriber.return_value = subscriber

    class Sub(RootType):
        @Entrypoint
        async def on_delete(self) -> AsyncGenerator[Task, None]:
            yield task

    resolver = ModelDeleteSubscriptionResolver(subscription=subscription, entrypoint=Sub.on_delete)

    with pytest.raises(GraphQLError):
        async for _ in resolver(None, mock_gql_info()):
            pass
