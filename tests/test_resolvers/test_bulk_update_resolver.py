from __future__ import annotations

import datetime
from inspect import isawaitable
from itertools import count
from typing import Any

import pytest
from asgiref.sync import sync_to_async
from graphql.pyutils import Path

from example_project.app.models import (
    Comment,
    Person,
    Project,
    Report,
    ServiceRequest,
    Task,
    TaskResult,
    TaskStep,
    TaskTypeChoices,
    Team,
)
from tests.factories import (
    PersonFactory,
    ProjectFactory,
    ReportFactory,
    ServiceRequestFactory,
    TaskFactory,
    TaskResultFactory,
    TaskStepFactory,
    TeamFactory,
)
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType
from undine.exceptions import GraphQLErrorGroup, GraphQLModelNotFoundError
from undine.resolvers import BulkUpdateResolver
from undine.utils.mutation_tree import bulk_mutate


@pytest.mark.django_db
def test_bulk_update_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.STORY)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.BUG_FIX)

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task_1.pk,
            "name": "Test task 1",
            "type": TaskTypeChoices.BUG_FIX.value,
        },
        {
            "pk": task_2.pk,
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    with patch_optimizer():
        results = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(results, list)
    assert len(results) == 2

    assert isinstance(results[0], Task)
    assert results[0].name == "Test task 1"
    assert results[0].type == TaskTypeChoices.BUG_FIX

    assert isinstance(results[1], Task)
    assert results[1].name == "Test task 2"
    assert results[1].type == TaskTypeChoices.STORY


@pytest.mark.django_db
def test_bulk_update_resolver__related_object_not_found(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create(request=None)

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "request": 1,
        },
    ]

    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    with patch_optimizer(), pytest.raises(GraphQLErrorGroup) as exc_info:
        resolver(root=None, info=mock_info, input=data)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLModelNotFoundError)
    assert errors[0].path == ["task", 0, "request"]


@pytest.mark.django_db
def test_bulk_update_resolver__forward_one_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedRequest(MutationType[ServiceRequest], kind="related"):
        details = Input()

    class TaskUpdateMutation(MutationType[Task]):
        request = Input(RelatedRequest)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "request": {
                "details": "Test request",
            },
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    request = ServiceRequest.objects.get(details="Test request")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].request == request


@pytest.mark.django_db
def test_bulk_update_resolver__forward_one_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()
    request = ServiceRequestFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "request": request.pk,
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].request == request


@pytest.mark.django_db
def test_bulk_update_resolver__forward_many_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()
    team = TeamFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedProject(MutationType[Project], kind="related"):
        name = Input()
        team = Input(Team)

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(RelatedProject)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "project": {
                "name": "Test project",
                "team": team.pk,
            },
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    project = Project.objects.get(name="Test project")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].project == project


@pytest.mark.django_db
def test_bulk_update_resolver__forward_many_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()
    project = ProjectFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "project": project.pk,
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].project == project


@pytest.mark.django_db
def test_bulk_update_resolver__forward_many_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedAssignee(MutationType[Person], kind="related"):
        name = Input()
        email = Input()

    class TaskUpdateMutation(MutationType[Task]):
        assignees = Input(RelatedAssignee, many=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "assignees": [
                {
                    "name": "Test assignee",
                    "email": "test@example.com",
                }
            ],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assignee = Person.objects.get(name="Test assignee")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert list(tasks[0].assignees.all()) == [assignee]


@pytest.mark.django_db
def test_bulk_update_resolver__forward_many_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()
    assignee = PersonFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "assignees": [assignee.pk],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert list(tasks[0].assignees.all()) == [assignee]


@pytest.mark.django_db
def test_bulk_update_resolver__reverse_one_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedResult(MutationType[TaskResult], kind="related"):
        details = Input()
        time_used = Input()

    class TaskUpdateMutation(MutationType[Task]):
        result = Input(RelatedResult)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "result": {
                "details": "Test result",
                "time_used": datetime.timedelta(seconds=10),
            },
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    result = TaskResult.objects.get(details="Test result")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].result == result


@pytest.mark.django_db
def test_bulk_update_resolver__reverse_one_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()
    result = TaskResultFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "result": result.pk,
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].result == result


@pytest.mark.django_db
def test_bulk_update_resolver__reverse_one_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedStep(MutationType[TaskStep], kind="related"):
        name = Input()

    class TaskUpdateMutation(MutationType[Task]):
        steps = Input(RelatedStep, many=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "steps": [
                {
                    "name": "Test step",
                }
            ],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    step = TaskStep.objects.get(name="Test step")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert list(tasks[0].steps.all()) == [step]


@pytest.mark.django_db
def test_bulk_update_resolver__reverse_one_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()
    step = TaskStepFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "steps": [step.pk],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert list(tasks[0].steps.all()) == [step]


@pytest.mark.django_db
def test_bulk_update_resolver__reverse_many_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedReport(MutationType[Report], kind="related"):
        name = Input()
        content = Input()

    class TaskUpdateMutation(MutationType[Task]):
        reports = Input(RelatedReport, many=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "reports": [
                {
                    "name": "Test report",
                    "content": "Test report content",
                },
            ],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    report = Report.objects.get(name="Test report")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert list(tasks[0].reports.all()) == [report]


@pytest.mark.django_db
def test_bulk_update_resolver__reverse_many_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()
    report = ReportFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "reports": [report.pk],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert list(tasks[0].reports.all()) == [report]


@pytest.mark.django_db
def test_bulk_update_resolver__generic_relation(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()
    commenter = PersonFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedComment(MutationType[Comment], kind="related"):
        contents = Input()
        commenter = Input(Person)

    class TaskUpdateMutation(MutationType[Task]):
        comments = Input(RelatedComment, many=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "comments": [
                {
                    "contents": "Test comment",
                    "commenter": commenter.pk,
                },
            ],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    comment = Comment.objects.get(contents="Test comment")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert list(tasks[0].comments.all()) == [comment]


@pytest.mark.django_db
def test_bulk_update_resolver__mutation_hooks(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create()

    counter = count()

    input_validate_called: int = -1
    input_permission_called: int = -1
    validate_called: int = -1
    permission_called: int = -1
    after_called: int = -1

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        name = Input()

        @name.validate
        def _(self, info: GQLInfo, value: str) -> None:
            nonlocal input_validate_called
            input_validate_called = next(counter)

        @name.permissions
        def _(self, info: GQLInfo, value: str) -> None:
            nonlocal input_permission_called
            input_permission_called = next(counter)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validate_called
            validate_called = next(counter)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal permission_called
            permission_called = next(counter)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal after_called
            after_called = next(counter)

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
        },
    ]

    with patch_optimizer():
        resolver(root=None, info=mock_gql_info(), input=data)

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert after_called == 4


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_bulk_update_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    task_1 = await sync_to_async(TaskFactory.create)(name="Task 1", type=TaskTypeChoices.STORY)
    task_2 = await sync_to_async(TaskFactory.create)(name="Task 2", type=TaskTypeChoices.BUG_FIX)

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.bulk_update_tasks)

    data = [
        {
            "pk": task_1.pk,
            "name": "Test task 1",
            "type": TaskTypeChoices.BUG_FIX.value,
        },
        {
            "pk": task_2.pk,
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    with patch_optimizer():
        results = resolver(root=None, info=mock_gql_info(), input=data)
        assert isawaitable(results)

        results = await results

    assert isinstance(results, list)
    assert len(results) == 2

    assert isinstance(results[0], Task)
    assert results[0].name == "Test task 1"
    assert results[0].type == TaskTypeChoices.BUG_FIX

    assert isinstance(results[1], Task)
    assert results[1].name == "Test task 2"
    assert results[1].type == TaskTypeChoices.STORY
