from __future__ import annotations

import datetime
from itertools import count
from typing import Any

import pytest

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
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType
from undine.exceptions import GraphQLModelNotFoundError
from undine.resolvers import BulkCreateResolver


@pytest.mark.django_db
def test_bulk_create_resolver() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.BUG_FIX.value,
        },
    ]

    with patch_optimizer():
        results = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(results, list)
    assert len(results) == 2

    assert isinstance(results[0], Task)
    assert results[0].name == "Test task 1"
    assert results[0].type == TaskTypeChoices.STORY

    assert isinstance(results[1], Task)
    assert results[1].name == "Test task 2"
    assert results[1].type == TaskTypeChoices.BUG_FIX


@pytest.mark.django_db
def test_bulk_create_resolver__related_object_not_found() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": 1,
        },
    ]

    with patch_optimizer(), pytest.raises(GraphQLModelNotFoundError):
        resolver(root=None, info=mock_gql_info(), input=data)


@pytest.mark.django_db
def test_bulk_create_resolver__forward_one_to_one() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
            "request": {
                "details": "Test request",
            },
        },
    ]

    with patch_optimizer():
        results = resolver(root=None, info=mock_gql_info(), input=data)

    request = ServiceRequest.objects.get(details="Test request")

    assert isinstance(results, list)
    assert len(results) == 1

    assert isinstance(results[0], Task)
    assert results[0].request == request


@pytest.mark.django_db
def test_bulk_create_resolver__forward_one_to_one__pk() -> None:
    request = ServiceRequestFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
        },
    ]

    with patch_optimizer():
        results = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(results, list)
    assert len(results) == 1

    assert isinstance(results[0], Task)
    assert results[0].request == request


@pytest.mark.django_db
def test_bulk_create_resolver__forward_many_to_one() -> None:
    team = TeamFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
            "project": {
                "name": "Test project",
                "team": team.pk,
            },
        },
    ]

    with patch_optimizer():
        results = resolver(root=None, info=mock_gql_info(), input=data)

    project = Project.objects.get(name="Test project")

    assert isinstance(results, list)
    assert len(results) == 1

    assert isinstance(results[0], Task)
    assert results[0].project == project


@pytest.mark.django_db
def test_bulk_create_resolver__forward_many_to_one__pk() -> None:
    project = ProjectFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
            "project": project.pk,
        },
    ]

    with patch_optimizer():
        results = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(results, list)
    assert len(results) == 1

    assert isinstance(results[0], Task)
    assert results[0].project == project


@pytest.mark.django_db
def test_bulk_create_resolver__forward_many_to_many() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
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

    assert tasks[0].name == "Test task"
    assert list(tasks[0].assignees.all()) == [assignee]


@pytest.mark.django_db
def test_bulk_create_resolver__forward_many_to_many__pk() -> None:
    assignee = PersonFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "assignees": [assignee.pk],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].name == "Test task"
    assert list(tasks[0].assignees.all()) == [assignee]


@pytest.mark.django_db
def test_bulk_create_resolver__reverse_one_to_one() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
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

    assert tasks[0].name == "Test task"
    assert tasks[0].result == result


@pytest.mark.django_db
def test_bulk_create_resolver__reverse_one_to_one__pk() -> None:
    result = TaskResultFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "result": result.pk,
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].name == "Test task"
    assert tasks[0].result == result


@pytest.mark.django_db
def test_bulk_create_resolver__reverse_one_to_many() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
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

    assert tasks[0].name == "Test task"
    assert list(tasks[0].steps.all()) == [step]


@pytest.mark.django_db
def test_bulk_create_resolver__reverse_one_to_many__pk() -> None:
    step = TaskStepFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "steps": [step.pk],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].name == "Test task"
    assert list(tasks[0].steps.all()) == [step]


@pytest.mark.django_db
def test_bulk_create_resolver__reverse_many_to_many() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "reports": [
                {
                    "name": "Test report",
                    "content": "Test report content",
                }
            ],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    report = Report.objects.get(name="Test report")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].name == "Test task"
    assert list(tasks[0].reports.all()) == [report]


@pytest.mark.django_db
def test_bulk_create_resolver__reverse_many_to_many__pk() -> None:
    report = ReportFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "reports": [report.pk],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].name == "Test task"
    assert list(tasks[0].reports.all()) == [report]


@pytest.mark.django_db
def test_bulk_create_resolver__generic_relation() -> None:
    commenter = PersonFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "comments": [{"contents": "Test comment", "commenter": commenter.pk}],
        },
    ]

    with patch_optimizer():
        tasks = resolver(root=None, info=mock_gql_info(), input=data)

    comment = Comment.objects.get(contents="Test comment")

    assert isinstance(tasks, list)
    assert len(tasks) == 1

    assert tasks[0].name == "Test task"
    assert list(tasks[0].comments.all()) == [comment]


@pytest.mark.django_db
def test_bulk_create_resolver__mutation_hooks() -> None:
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
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    with patch_optimizer():
        resolver(root=None, info=mock_gql_info(), input=data)

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert after_called == 4
