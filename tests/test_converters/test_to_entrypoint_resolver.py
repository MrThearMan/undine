from example_project.app.models import Task
from undine import Entrypoint, MutationType, QueryType, RootOperationType
from undine.converters import convert_entrypoint_ref_to_resolver
from undine.resolvers import (
    BulkCreateResolver,
    BulkDeleteResolver,
    BulkUpdateResolver,
    CreateResolver,
    CustomResolver,
    DeleteResolver,
    FunctionResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
    UpdateResolver,
)
from undine.typing import GQLInfo


def test_convert_entrypoint_ref_to_resolver__function():
    def func() -> int: ...

    result = convert_entrypoint_ref_to_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param is None
    assert result.info_param is None


def test_convert_entrypoint_ref_to_resolver__function__info_param():
    def func(info: GQLInfo) -> int: ...

    result = convert_entrypoint_ref_to_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param is None
    assert result.info_param == "info"


def test_convert_entrypoint_ref_to_resolver__function__root_param():
    def func(root) -> int: ...

    result = convert_entrypoint_ref_to_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param == "root"
    assert result.info_param is None


def test_convert_entrypoint_ref_to_resolver__function__root_param__self():
    def func(self) -> int: ...

    result = convert_entrypoint_ref_to_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param == "self"
    assert result.info_param is None


def test_convert_entrypoint_ref_to_resolver__function__root_param__cls():
    def func(cls) -> int: ...

    result = convert_entrypoint_ref_to_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param == "cls"
    assert result.info_param is None


def test_convert_entrypoint_ref_to_resolver__query_type():
    class TaskType(QueryType, model=Task): ...

    class Query(RootOperationType):
        task = Entrypoint(TaskType)

    result = convert_entrypoint_ref_to_resolver(TaskType, caller=Query.task)

    assert isinstance(result, QueryTypeSingleResolver)


def test_convert_entrypoint_ref_to_resolver__query_type__many():
    class TaskType(QueryType, model=Task): ...

    class Query(RootOperationType):
        task = Entrypoint(TaskType, many=True)

    result = convert_entrypoint_ref_to_resolver(TaskType, caller=Query.task)

    assert isinstance(result, QueryTypeManyResolver)


def test_convert_entrypoint_ref_to_resolver__mutation_type__create_mutation():
    class TaskCreateMutation(MutationType, model=Task): ...

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    result = convert_entrypoint_ref_to_resolver(TaskCreateMutation, caller=Mutation.create_task)

    assert isinstance(result, CreateResolver)
    assert result.mutation_type == TaskCreateMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__update_mutation():
    class TaskUpdateMutation(MutationType, model=Task): ...

    class Mutation:
        update_task = Entrypoint(TaskUpdateMutation)

    result = convert_entrypoint_ref_to_resolver(TaskUpdateMutation, caller=Mutation.update_task)

    assert isinstance(result, UpdateResolver)
    assert result.mutation_type == TaskUpdateMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__delete_mutation():
    class TaskDeleteMutation(MutationType, model=Task): ...

    class Mutation:
        delete_task = Entrypoint(TaskDeleteMutation)

    result = convert_entrypoint_ref_to_resolver(TaskDeleteMutation, caller=Mutation.delete_task)

    assert isinstance(result, DeleteResolver)
    assert result.mutation_type == TaskDeleteMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__custom_mutation():
    class TaskMutation(MutationType, model=Task): ...

    class Mutation:
        mutate_task = Entrypoint(TaskMutation)

    result = convert_entrypoint_ref_to_resolver(TaskMutation, caller=Mutation.mutate_task)

    assert isinstance(result, CustomResolver)
    assert result.mutation_type == TaskMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__many__create_mutation():
    class TaskBulkCreateMutation(MutationType, model=Task): ...

    class Mutation:
        bulk_create_task = Entrypoint(TaskBulkCreateMutation, many=True)

    result = convert_entrypoint_ref_to_resolver(TaskBulkCreateMutation, caller=Mutation.bulk_create_task)

    assert isinstance(result, BulkCreateResolver)
    assert result.mutation_type == TaskBulkCreateMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__many__update_mutation():
    class TaskBulkUpdateMutation(MutationType, model=Task): ...

    class Mutation:
        bulk_update_task = Entrypoint(TaskBulkUpdateMutation, many=True)

    result = convert_entrypoint_ref_to_resolver(TaskBulkUpdateMutation, caller=Mutation.bulk_update_task)

    assert isinstance(result, BulkUpdateResolver)
    assert result.mutation_type == TaskBulkUpdateMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__many__delete_mutation():
    class TaskBulkDeleteMutation(MutationType, model=Task): ...

    class Mutation:
        bulk_delete_task = Entrypoint(TaskBulkDeleteMutation, many=True)

    result = convert_entrypoint_ref_to_resolver(TaskBulkDeleteMutation, caller=Mutation.bulk_delete_task)

    assert isinstance(result, BulkDeleteResolver)
    assert result.mutation_type == TaskBulkDeleteMutation


def test_convert_entrypoint_ref_to_resolver__mutation_type__many__custom_mutation():
    class TaskMutation(MutationType, model=Task): ...

    class Mutation:
        bulk_mutation = Entrypoint(TaskMutation, many=True)

    result = convert_entrypoint_ref_to_resolver(TaskMutation, caller=Mutation.bulk_mutation)

    assert isinstance(result, CustomResolver)
    assert result.mutation_type == TaskMutation
