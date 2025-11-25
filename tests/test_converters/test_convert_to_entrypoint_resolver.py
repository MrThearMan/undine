from __future__ import annotations

from typing import Any

import pytest
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from undine import Entrypoint, Input, InterfaceField, InterfaceType, MutationType, QueryType, RootType, UnionType
from undine.converters import convert_to_entrypoint_resolver
from undine.exceptions import InvalidEntrypointMutationTypeError
from undine.pagination import OffsetPagination
from undine.relay import Connection, Node
from undine.resolvers import (
    BulkCreateResolver,
    BulkDeleteResolver,
    BulkUpdateResolver,
    ConnectionResolver,
    CreateResolver,
    DeleteResolver,
    EntrypointFunctionResolver,
    InterfaceTypeConnectionResolver,
    InterfaceTypeResolver,
    NodeResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
    UnionTypeConnectionResolver,
    UnionTypeResolver,
    UpdateResolver,
)
from undine.typing import GQLInfo


def test_convert_entrypoint_ref_to_resolver__function() -> None:
    def func() -> int:
        return 1

    class Query(RootType):
        example = Entrypoint(func)

    result = convert_to_entrypoint_resolver(func, caller=Query.example)

    assert isinstance(result, EntrypointFunctionResolver)

    assert result.func == func
    assert result.root_param is None
    assert result.info_param is None


def test_convert_entrypoint_ref_to_resolver__function__info_param() -> None:
    def func(info: GQLInfo) -> int:
        return 1

    class Query(RootType):
        example = Entrypoint(func)

    result = convert_to_entrypoint_resolver(func, caller=Query.example)

    assert isinstance(result, EntrypointFunctionResolver)

    assert result.func == func
    assert result.root_param is None
    assert result.info_param == "info"


def test_convert_entrypoint_ref_to_resolver__function__root_param() -> None:
    def func(root) -> int:
        return 1

    class Query(RootType):
        example = Entrypoint(func)

    result = convert_to_entrypoint_resolver(func, caller=Query.example)

    assert isinstance(result, EntrypointFunctionResolver)

    assert result.func == func
    assert result.root_param == "root"
    assert result.info_param is None


def test_convert_entrypoint_ref_to_resolver__function__root_param__self() -> None:
    def func(self) -> int:
        return 1

    class Query(RootType):
        example = Entrypoint(func)

    result = convert_to_entrypoint_resolver(func, caller=Query.example)

    assert isinstance(result, EntrypointFunctionResolver)

    assert result.func == func
    assert result.root_param == "self"
    assert result.info_param is None


def test_convert_entrypoint_ref_to_resolver__function__root_param__cls() -> None:
    def func(cls) -> int:
        return 1

    class Query(RootType):
        example = Entrypoint(func)

    result = convert_to_entrypoint_resolver(func, caller=Query.example)

    assert isinstance(result, EntrypointFunctionResolver)

    assert result.func == func
    assert result.root_param == "cls"
    assert result.info_param is None


def test_convert_entrypoint_ref_to_resolver__query_type() -> None:
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    result = convert_to_entrypoint_resolver(TaskType, caller=Query.task)

    assert isinstance(result, QueryTypeSingleResolver)


def test_convert_entrypoint_ref_to_resolver__query_type__many() -> None:
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, many=True)

    result = convert_to_entrypoint_resolver(TaskType, caller=Query.task)

    assert isinstance(result, QueryTypeManyResolver)


def test_convert_entrypoint_ref_to_resolver__mutation_type__create_mutation() -> None:
    class TaskCreateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    result = convert_to_entrypoint_resolver(TaskCreateMutation, caller=Mutation.create_task)

    assert isinstance(result, CreateResolver)
    assert result.mutation_type == TaskCreateMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__update_mutation() -> None:
    class TaskUpdateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    result = convert_to_entrypoint_resolver(TaskUpdateMutation, caller=Mutation.update_task)

    assert isinstance(result, UpdateResolver)
    assert result.mutation_type == TaskUpdateMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__delete_mutation() -> None:
    class TaskDeleteMutation(MutationType[Task]): ...

    class Mutation(RootType):
        delete_task = Entrypoint(TaskDeleteMutation)

    result = convert_to_entrypoint_resolver(TaskDeleteMutation, caller=Mutation.delete_task)

    assert isinstance(result, DeleteResolver)
    assert result.mutation_type == TaskDeleteMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__custom_mutation__create() -> None:
    class TaskMutation(MutationType[Task]):
        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Any:
            return instance

    class Mutation(RootType):
        mutate_task = Entrypoint(TaskMutation)

    result = convert_to_entrypoint_resolver(TaskMutation, caller=Mutation.mutate_task)

    assert isinstance(result, CreateResolver)
    assert result.mutation_type == TaskMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__custom_mutation__update() -> None:
    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Any:
            return instance

    class Mutation(RootType):
        mutate_task = Entrypoint(TaskMutation)

    result = convert_to_entrypoint_resolver(TaskMutation, caller=Mutation.mutate_task)

    assert isinstance(result, UpdateResolver)
    assert result.mutation_type == TaskMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__custom_mutation__bulk_create() -> None:
    class TaskMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> Any:
            return instances

    class Mutation(RootType):
        mutate_task = Entrypoint(TaskMutation, many=True)

    result = convert_to_entrypoint_resolver(TaskMutation, caller=Mutation.mutate_task)

    assert isinstance(result, BulkCreateResolver)
    assert result.mutation_type == TaskMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__custom_mutation__bulk_update() -> None:
    class TaskMutation(MutationType[Task]):
        pk = Input(required=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> Any:
            return instances

    class Mutation(RootType):
        mutate_task = Entrypoint(TaskMutation, many=True)

    result = convert_to_entrypoint_resolver(TaskMutation, caller=Mutation.mutate_task)

    assert isinstance(result, BulkUpdateResolver)
    assert result.mutation_type == TaskMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__many__create_mutation() -> None:
    class TaskBulkCreateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskBulkCreateMutation, many=True)

    result = convert_to_entrypoint_resolver(TaskBulkCreateMutation, caller=Mutation.bulk_create_task)

    assert isinstance(result, BulkCreateResolver)
    assert result.mutation_type == TaskBulkCreateMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__many__update_mutation() -> None:
    class TaskBulkUpdateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskBulkUpdateMutation, many=True)

    result = convert_to_entrypoint_resolver(TaskBulkUpdateMutation, caller=Mutation.bulk_update_task)

    assert isinstance(result, BulkUpdateResolver)
    assert result.mutation_type == TaskBulkUpdateMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__many__delete_mutation() -> None:
    class TaskBulkDeleteMutation(MutationType[Task]): ...

    class Mutation(RootType):
        bulk_delete_task = Entrypoint(TaskBulkDeleteMutation, many=True)

    result = convert_to_entrypoint_resolver(TaskBulkDeleteMutation, caller=Mutation.bulk_delete_task)

    assert isinstance(result, BulkDeleteResolver)
    assert result.mutation_type == TaskBulkDeleteMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__related() -> None:
    class TaskMutation(MutationType[Task], kind="related"): ...

    class Mutation(RootType):
        bad_mutation = Entrypoint(TaskMutation)

    with pytest.raises(InvalidEntrypointMutationTypeError):
        convert_to_entrypoint_resolver(TaskMutation, caller=Mutation.bad_mutation)


def test_convert_entrypoint_ref_to_resolver__offset_pagination__query_type() -> None:
    class TaskType(QueryType[Task]): ...

    pagination = OffsetPagination(TaskType)

    class Query(RootType):
        tasks = Entrypoint(pagination)

    resolver = convert_to_entrypoint_resolver(pagination, caller=Query.tasks)

    assert isinstance(resolver, QueryTypeManyResolver)


def test_convert_entrypoint_ref_to_resolver__offset_pagination__union_type() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class Commentable(UnionType[TaskType, ProjectType]): ...

    pagination = OffsetPagination(Commentable)

    class Query(RootType):
        commentable = Entrypoint(pagination)

    resolver = convert_to_entrypoint_resolver(pagination, caller=Query.commentable)

    assert isinstance(resolver, UnionTypeResolver)


def test_convert_entrypoint_ref_to_resolver__offset_pagination__interface_type() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task]): ...

    pagination = OffsetPagination(Named)

    class Query(RootType):
        named = Entrypoint(pagination)

    resolver = convert_to_entrypoint_resolver(pagination, caller=Query.named)

    assert isinstance(resolver, InterfaceTypeResolver)


def test_convert_entrypoint_ref_to_resolver__connection__query_type() -> None:
    class TaskType(QueryType[Task]): ...

    pagination = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(pagination)

    resolver = convert_to_entrypoint_resolver(pagination, caller=Query.tasks)

    assert isinstance(resolver, ConnectionResolver)


def test_convert_entrypoint_ref_to_resolver__connection__union_type() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class Commentable(UnionType[TaskType, ProjectType]): ...

    pagination = Connection(Commentable)

    class Query(RootType):
        commentable = Entrypoint(pagination)

    resolver = convert_to_entrypoint_resolver(pagination, caller=Query.commentable)

    assert isinstance(resolver, UnionTypeConnectionResolver)


def test_convert_entrypoint_ref_to_resolver__connection__interface_type() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task]): ...

    pagination = Connection(Named)

    class Query(RootType):
        named = Entrypoint(pagination)

    resolver = convert_to_entrypoint_resolver(pagination, caller=Query.named)

    assert isinstance(resolver, InterfaceTypeConnectionResolver)


def test_convert_entrypoint_ref_to_resolver__union_type() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(Commentable)

    resolver = convert_to_entrypoint_resolver(Commentable, caller=Query.commentable)

    assert isinstance(resolver, UnionTypeResolver)


def test_convert_entrypoint_ref_to_resolver__interface_type() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        named = Entrypoint(Named)

    resolver = convert_to_entrypoint_resolver(Named, caller=Query.named)

    assert isinstance(resolver, InterfaceTypeResolver)


def test_convert_entrypoint_ref_to_resolver__node() -> None:
    @Node
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        node = Entrypoint(Node)

    resolver = convert_to_entrypoint_resolver(Node, caller=Query.node)

    assert isinstance(resolver, NodeResolver)
