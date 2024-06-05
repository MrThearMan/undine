from __future__ import annotations

import pytest

from example_project.app.models import Task
from undine import Entrypoint, MutationType, QueryType, RootType
from undine.converters import convert_to_entrypoint_resolver
from undine.exceptions import InvalidEntrypointMutationTypeError
from undine.resolvers import (
    BulkCreateResolver,
    BulkDeleteResolver,
    BulkUpdateResolver,
    CreateResolver,
    CustomResolver,
    DeleteResolver,
    EntrypointFunctionResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
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


def test_convert_entrypoint_ref_to_resolver__mutation_type__custom_mutation() -> None:
    class TaskMutation(MutationType[Task]): ...

    class Mutation(RootType):
        mutate_task = Entrypoint(TaskMutation)

    result = convert_to_entrypoint_resolver(TaskMutation, caller=Mutation.mutate_task)

    assert isinstance(result, CustomResolver)
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


def test_convert_entrypoint_ref_to_resolver__mutation_type__many__custom_mutation() -> None:
    class TaskMutation(MutationType[Task]): ...

    class Mutation(RootType):
        bulk_mutation = Entrypoint(TaskMutation, many=True)

    result = convert_to_entrypoint_resolver(TaskMutation, caller=Mutation.bulk_mutation)

    assert isinstance(result, CustomResolver)
    assert result.mutation_type == TaskMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__related() -> None:
    class TaskMutation(MutationType[Task], kind="related"): ...

    class Mutation(RootType):
        bad_mutation = Entrypoint(TaskMutation)

    with pytest.raises(InvalidEntrypointMutationTypeError):
        convert_to_entrypoint_resolver(TaskMutation, caller=Mutation.bad_mutation)
