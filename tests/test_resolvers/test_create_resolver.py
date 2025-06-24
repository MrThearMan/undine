from __future__ import annotations

import datetime
from inspect import isawaitable
from itertools import count
from typing import Any

import pytest

from example_project.app.models import (
    Person,
    Project,
    Report,
    ServiceRequest,
    Task,
    TaskResult,
    TaskStep,
    TaskTypeChoices,
)
from tests.factories import (
    PersonFactory,
    ProjectFactory,
    ReportFactory,
    ServiceRequestFactory,
    TaskResultFactory,
    TaskStepFactory,
    TeamFactory,
)
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, Input, MutationType, QueryType, RootType
from undine.resolvers import CreateResolver
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_create_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, Task)
    assert tasks.name == "Test task"
    assert tasks.type == TaskTypeChoices.STORY


@pytest.mark.django_db
def test_create_resolver__forward_one_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": {
            "details": "Test request",
        },
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    request = ServiceRequest.objects.get(details="Test request")

    assert isinstance(tasks, Task)
    assert tasks.request == request


@pytest.mark.django_db
def test_create_resolver__forward_one_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    request = ServiceRequestFactory.create(details="Test request")

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": request.pk,
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, Task)
    assert tasks.request == request


@pytest.mark.django_db
def test_create_resolver__forward_many_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    team = TeamFactory.create(name="Test team")

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "project": {
            "name": "Test project",
            "team": team.pk,
        },
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    project = Project.objects.get(name="Test project")

    assert isinstance(tasks, Task)
    assert tasks.project == project


@pytest.mark.django_db
def test_create_resolver__forward_many_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    project = ProjectFactory.create(name="Test project")

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "project": project.pk,
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, Task)
    assert tasks.project == project


@pytest.mark.django_db
def test_create_resolver__forward_many_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "assignees": [
            {
                "name": "Test assignee",
                "email": "test@example.com",
            },
        ],
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    person = Person.objects.get(name="Test assignee")

    assert isinstance(tasks, Task)
    assert list(tasks.assignees.all()) == [person]


@pytest.mark.django_db
def test_create_resolver__forward_many_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    person = PersonFactory.create(name="Test assignee")

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "assignees": [person.pk],
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, Task)
    assert list(tasks.assignees.all()) == [person]


@pytest.mark.django_db
def test_create_resolver__reverse_one_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "result": {
            "details": "Test result",
            "time_used": datetime.timedelta(seconds=10),
        },
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    result = TaskResult.objects.get(details="Test result")

    assert isinstance(tasks, Task)
    assert tasks.result == result


@pytest.mark.django_db
def test_create_resolver__reverse_one_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    result = TaskResultFactory.create(details="Test result")

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "result": result.pk,
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, Task)
    assert tasks.result == result


@pytest.mark.django_db
def test_create_resolver__reverse_one_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "steps": [
            {
                "name": "Test step",
            },
        ],
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    step = TaskStep.objects.get(name="Test step")

    assert isinstance(tasks, Task)
    assert list(tasks.steps.all()) == [step]


@pytest.mark.django_db
def test_create_resolver__reverse_one_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    step = TaskStepFactory.create(name="Test step")

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "steps": [step.pk],
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, Task)
    assert list(tasks.steps.all()) == [step]


@pytest.mark.django_db
def test_create_resolver__reverse_many_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "reports": [
            {
                "name": "Test report",
                "content": "Test report content",
            },
        ],
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    report = Report.objects.get(name="Test report")

    assert isinstance(tasks, Task)
    assert list(tasks.reports.all()) == [report]


@pytest.mark.django_db
def test_create_resolver__reverse_many_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    report = ReportFactory.create(name="Test report")

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "reports": [report.pk],
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, Task)
    assert list(tasks.reports.all()) == [report]


@pytest.mark.django_db
def test_create_resolver__mutation_hooks(undine_settings) -> None:
    undine_settings.ASYNC = False

    counter = count()

    input_validate_called: int = -1
    input_permission_called: int = -1
    validate_called: int = -1
    permission_called: int = -1
    after_called: int = -1

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        name = Input()

        @name.validate
        def _(self: Task, info: GQLInfo, value: str) -> None:
            nonlocal input_validate_called
            input_validate_called = next(counter)

        @name.permissions
        def _(self: Task, info: GQLInfo, value: str) -> None:
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
        def __after__(cls, instance: Task, info: GQLInfo, previous_data: dict[str, Any]) -> None:
            nonlocal after_called
            after_called = next(counter)

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
    }

    with patch_optimizer():
        resolver(root=None, info=mock_gql_info(), input=data)

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert after_called == 4


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_create_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = CreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.create_task)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
    }

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)
        assert isawaitable(tasks)

        tasks = await tasks

    assert isinstance(tasks, Task)
    assert tasks.name == "Test task"
    assert tasks.type == TaskTypeChoices.STORY
