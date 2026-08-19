from __future__ import annotations

from typing import Any

import pytest

from example_project.app.models import Task, Project
from tests.helpers import mock_gql_info
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import EntrypointFunctionResolver


async def test_resolvers__function_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @Field
        async def computed(self) -> str:
            return "async_result"

    resolver = TaskType.computed.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "async_result"


async def test_resolvers__function_resolver__async__check_permissions_async__many_sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:
        called_with.append(item)

    async def func() -> list[str]:  # noqa: RUF029
        return ["a", "b"]

    class Query(RootType):
        example = Entrypoint(func, many=True)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = await resolver(root=None, info=mock_gql_info())

    assert result == ["a", "b"]
    assert called_with == ["a", "b"]


async def test_resolvers__function_resolver__async__check_permissions_async__many_sync_func_2(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        @Field(many=True)
        async def tags(self) -> list[str]:
            return ["x", "y"]

        @tags.permissions
        def tags_permissions(self, info: GQLInfo, item: str) -> None:
            called_with.append(item)

    resolver = TaskType.tags.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == ["x", "y"]
    assert called_with == ["x", "y"]


async def test_resolvers__function_resolver__async__check_permissions_async__many_async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    async def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:  # noqa: RUF029
        called_with.append(item)

    async def func() -> list[str]:  # noqa: RUF029
        return ["a", "b"]

    class Query(RootType):
        example = Entrypoint(func, many=True)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = await resolver(root=None, info=mock_gql_info())

    assert result == ["a", "b"]
    assert called_with == ["a", "b"]


async def test_resolvers__function_resolver__async__check_permissions_async__many_async_func_2(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        @Field(many=True)
        async def tags(self) -> list[str]:
            return ["x", "y"]

        @tags.permissions
        async def tags_permissions(self, info: GQLInfo, item: str) -> None:
            called_with.append(item)

    resolver = TaskType.tags.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == ["x", "y"]
    assert called_with == ["x", "y"]


async def test_resolvers__function_resolver__async__check_permissions_async__single_async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    async def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:  # noqa: RUF029
        called_with.append(item)

    async def func() -> str:  # noqa: RUF029
        return "result"

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "result"
    assert called_with == ["result"]


async def test_resolvers__function_resolver__async__check_permissions_async__single_async_func_2(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        @Field
        async def computed(self) -> str:
            return "val"

        @computed.permissions
        async def computed_permissions(self, info: GQLInfo, value: str) -> None:
            called_with.append(value)

    resolver = TaskType.computed.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "val"
    assert called_with == ["val"]


async def test_resolvers__function_resolver__async__check_permissions_async__single_sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:
        called_with.append(item)

    async def func() -> str:  # noqa: RUF029
        return "result"

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "result"
    assert called_with == ["result"]


async def test_resolvers__function_resolver__async__check_permissions_async__single_sync_func_2(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        @Field
        async def computed(self) -> str:
            return "val"

        @computed.permissions
        def computed_permissions(self, info: GQLInfo, value: str) -> None:
            called_with.append(value)

    resolver = TaskType.computed.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "val"
    assert called_with == ["val"]


async def test_resolvers__function_resolver__async__check_permissions_async__query_type_async_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        async def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    async def func() -> Any:  # noqa: RUF029
        return object()

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.ref = TaskType

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)

    with pytest.raises(GraphQLPermissionError):
        await resolver(root=None, info=mock_gql_info())


async def test_resolvers__function_resolver__async__check_permissions_async__query_type_sync_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    async def func() -> Any:  # noqa: RUF029
        return object()

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.ref = TaskType

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)

    with pytest.raises(GraphQLPermissionError):
        await resolver(root=None, info=mock_gql_info())


async def test_resolvers__function_resolver__async__set_kwargs__info_only(undine_settings) -> None:
    undine_settings.ASYNC = True

    captured = []

    class TaskType(QueryType[Task]):
        @Field
        @staticmethod
        async def computed(info: GQLInfo) -> str:  # no root param
            captured.append(info)
            return "result"

    resolver = TaskType.computed.get_resolver()
    info = mock_gql_info()
    result = await resolver(root=None, info=info)

    assert result == "result"
    assert captured == [info]


async def test_resolvers__function_resolver__async__check_permissions_async__query_type_async(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]):
        @classmethod
        async def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.resolve
        async def resolve_project(self) -> Any:
            return object()

    resolver = TaskType.project.get_resolver()

    with pytest.raises(GraphQLPermissionError):
        await resolver(root=None, info=mock_gql_info())


async def test_resolvers__function_resolver__async__check_permissions_async__query_type_sync(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]):
        @classmethod
        def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.resolve
        async def resolve_project(self) -> Any:
            return object()

    resolver = TaskType.project.get_resolver()

    with pytest.raises(GraphQLPermissionError):
        await resolver(root=None, info=mock_gql_info())
