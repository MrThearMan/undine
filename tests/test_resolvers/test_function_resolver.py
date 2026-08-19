from __future__ import annotations

from typing import Any

import pytest
from graphql import GraphQLResolveInfo

from example_project.app.models import Task, Project
from tests.helpers import mock_gql_info
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import EntrypointFunctionResolver


def test_resolvers__function_resolver() -> None:
    def func() -> str:
        return "foo"

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__root() -> None:
    def func(root: Any) -> Any:
        return root

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root="foo", info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__info() -> None:
    def func(info: GQLInfo) -> Any:
        return info

    class Query(RootType):
        example = Entrypoint(func)

    gql_info = mock_gql_info()
    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=gql_info)
    assert result == gql_info


def test_resolvers__function_resolver__adapt() -> None:
    def func() -> str:
        return "foo"

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root() -> None:
    def func(root: Any) -> Any:
        return root

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root="foo", info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root__self() -> None:
    def func(self: Any) -> Any:
        return self

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root="foo", info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root__cls() -> None:
    def func(cls: Any) -> Any:
        return cls

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root="foo", info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__info() -> None:
    def func(info: GQLInfo) -> Any:
        return info

    class Query(RootType):
        example = Entrypoint(func)

    info = mock_gql_info()
    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=info)
    assert result == info


def test_resolvers__function_resolver__adapt__info__graphql_resolver_info() -> None:
    def func(info: GraphQLResolveInfo) -> Any:
        return info

    class Query(RootType):
        example = Entrypoint(func)

    info = mock_gql_info()
    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=info)
    assert result == info


def test_resolvers__function_resolver__field_permissions() -> None:
    class TaskType(QueryType[Task]):
        @Field
        def name(self) -> str:
            return "foo"

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver = TaskType.name.get_resolver()

    with pytest.raises(GraphQLPermissionError):
        resolver(root=None, info=mock_gql_info())


def test_resolvers__function_resolver__check_permissions__many_with_permissions_func() -> None:
    called_with = []

    def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:
        called_with.append(item)

    def func() -> list[str]:
        return ["a", "b"]

    class Query(RootType):
        example = Entrypoint(func, many=True)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=mock_gql_info())

    assert result == ["a", "b"]
    assert called_with == ["a", "b"]


def test_resolvers__function_resolver__check_permissions__many_with_permissions_func_2() -> None:
    called_with = []

    class TaskType(QueryType[Task]):
        @Field(many=True)
        def tags(self) -> list[str]:
            return ["a", "b"]

        @tags.permissions
        def tags_permissions(self, info: GQLInfo, item: str) -> None:
            called_with.append(item)

    resolver = TaskType.tags.get_resolver()
    result = resolver(root=None, info=mock_gql_info())

    assert result == ["a", "b"]
    assert called_with == ["a", "b"]


def test_resolvers__function_resolver__check_permissions__single_with_permissions_func() -> None:
    called_with = []

    def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:
        called_with.append(item)

    def func() -> str:
        return "result"

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=mock_gql_info())

    assert result == "result"
    assert called_with == ["result"]


def test_resolvers__function_resolver__check_permissions__query_type_permissions() -> None:
    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    def func() -> Any:
        return object()

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.ref = TaskType

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)

    with pytest.raises(GraphQLPermissionError):
        resolver(root=None, info=mock_gql_info())


def test_resolvers__function_resolver__check_permissions__query_type_permissions_2() -> None:
    class ProjectType(QueryType[Project]):
        @classmethod
        def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.resolve
        def resolve_project(self) -> Any:
            return object()

    resolver = TaskType.project.get_resolver()

    with pytest.raises(GraphQLPermissionError):
        resolver(root=None, info=mock_gql_info())
