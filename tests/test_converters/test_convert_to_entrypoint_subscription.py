from __future__ import annotations

from typing import AsyncGenerator, AsyncIterable, AsyncIterator, Generator, Self

from example_project.app.models import Project, Task
from undine import Entrypoint, InterfaceType, MutationType, QueryType, RootType, UnionType
from undine.converters import convert_to_entrypoint_subscription
from undine.relay import Connection, Node
from undine.resolvers import EntrypointFunctionSubscription


def test_convert_to_entrypoint_subscription__async_generator() -> None:
    async def func() -> AsyncGenerator[int, None]:  # noqa: RUF029
        for i in range(2):
            yield i

    class Subscription(RootType):
        fn = Entrypoint(func)

    resolver = EntrypointFunctionSubscription(func=func, entrypoint=Subscription.fn)

    assert convert_to_entrypoint_subscription(func, caller=Subscription.fn) == resolver


def test_convert_to_entrypoint_subscription__coroutine_returning_async_iterator() -> None:
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

    async def func() -> AsyncIterator[int]:  # noqa: RUF029
        return ExampleIterator()

    class Subscription(RootType):
        fn = Entrypoint(func)

    resolver = EntrypointFunctionSubscription(func=func, entrypoint=Subscription.fn)

    assert convert_to_entrypoint_subscription(func, caller=Subscription.fn) == resolver


def test_convert_to_entrypoint_subscription__coroutine_returning_async_iterable() -> None:
    class ExampleIterable:
        def __aiter__(self) -> AsyncIterator[int]:
            return self.gen()

        async def gen(self) -> AsyncGenerator[int, None]:
            for i in range(2):
                yield i

    async def func() -> AsyncIterable[int]:  # noqa: RUF029
        return ExampleIterable()

    class Subscription(RootType):
        fn = Entrypoint(func)

    resolver = EntrypointFunctionSubscription(func=func, entrypoint=Subscription.fn)

    assert convert_to_entrypoint_subscription(func, caller=Subscription.fn) == resolver


def test_convert_to_entrypoint_subscription__regular_function() -> None:
    def func() -> int:
        return 1

    class Subscription(RootType):
        fn = Entrypoint(func)

    assert convert_to_entrypoint_subscription(func, caller=Subscription.fn) is None


def test_convert_to_entrypoint_subscription__generator_function() -> None:
    def func() -> Generator[int, None, None]:
        for i in range(2):
            yield i

    class Subscription(RootType):
        fn = Entrypoint(func)

    assert convert_to_entrypoint_subscription(func, caller=Subscription.fn) is None


def test_convert_to_entrypoint_subscription__query_type() -> None:
    class TaskType(QueryType[Task]): ...

    class Subscription(RootType):
        tasks = Entrypoint(TaskType)

    assert convert_to_entrypoint_subscription(TaskType, caller=Subscription.tasks) is None


def test_convert_to_entrypoint_subscription__mutation_type() -> None:
    class CreateTaskMutation(MutationType[Task]): ...

    class Subscription(RootType):
        create_task = Entrypoint(CreateTaskMutation)

    assert convert_to_entrypoint_subscription(CreateTaskMutation, caller=Subscription.create_task) is None


def test_convert_to_entrypoint_subscription__union_type() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Subscription(RootType):
        commentable = Entrypoint(Commentable)

    assert convert_to_entrypoint_subscription(Commentable, caller=Subscription.commentable) is None


def test_convert_to_entrypoint_subscription__node() -> None:
    class Subscription(RootType):
        node = Entrypoint(Node)

    assert convert_to_entrypoint_subscription(Node, caller=Subscription.node) is None


def test_convert_to_entrypoint_subscription__interface_type() -> None:
    class MyInterface(InterfaceType): ...

    class Subscription(RootType):
        inter = Entrypoint(MyInterface)

    assert convert_to_entrypoint_subscription(MyInterface, caller=Subscription.inter) is None


def test_convert_to_entrypoint_subscription__connection() -> None:
    class TaskType(QueryType[Task]): ...

    class Subscription(RootType):
        tasks = Entrypoint(Connection(TaskType))

    assert convert_to_entrypoint_subscription(TaskType, caller=Subscription.tasks) is None
