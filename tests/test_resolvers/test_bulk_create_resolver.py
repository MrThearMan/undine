from __future__ import annotations

import datetime
from inspect import isawaitable
from itertools import count
from typing import Any

import pytest
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
    TaskResultFactory,
    TaskStepFactory,
    TeamFactory,
)
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType
from undine.exceptions import GraphQLErrorGroup, GraphQLModelNotFoundError
from undine.resolvers import BulkCreateResolver
from undine.utils.mutation_tree import bulk_mutate


@pytest.mark.django_db
def test_bulk_create_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

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
def test_bulk_create_resolver__related_object_not_found(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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

    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    with patch_optimizer(), pytest.raises(GraphQLErrorGroup) as exc_info:
        resolver(root=None, info=mock_info, input=data)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLModelNotFoundError)
    assert errors[0].path == ["task", 0, "request"]


@pytest.mark.django_db
def test_bulk_create_resolver__forward_one_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class RelatedRequest(MutationType[ServiceRequest], kind="related"):
        details = Input()

    class TaskCreateMutation(MutationType[Task]):
        request = Input(RelatedRequest)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__forward_one_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    request = ServiceRequestFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__forward_many_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    team = TeamFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedProject(MutationType[Project], kind="related"):
        name = Input()
        team = Input(Team)

    class TaskCreateMutation(MutationType[Task]):
        project = Input(RelatedProject)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__forward_many_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    project = ProjectFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__forward_many_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class RelatedAssignee(MutationType[Person], kind="related"):
        name = Input()
        email = Input()

    class TaskCreateMutation(MutationType[Task]):
        assignees = Input(RelatedAssignee, many=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__forward_many_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    assignee = PersonFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__reverse_one_to_one(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class RelatedResult(MutationType[TaskResult], kind="related"):
        details = Input()
        time_used = Input()

    class TaskCreateMutation(MutationType[Task]):
        result = Input(RelatedResult)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__reverse_one_to_one__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    result = TaskResultFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__reverse_one_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class RelatedStep(MutationType[TaskStep], kind="related"):
        name = Input()

    class TaskCreateMutation(MutationType[Task]):
        steps = Input(RelatedStep, many=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__reverse_one_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    step = TaskStepFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__reverse_many_to_many(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class RelatedReport(MutationType[Report], kind="related"):
        name = Input()
        content = Input()

    class TaskCreateMutation(MutationType[Task]):
        reports = Input(RelatedReport, many=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__reverse_many_to_many__pk(undine_settings) -> None:
    undine_settings.ASYNC = False

    report = ReportFactory.create()

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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
def test_bulk_create_resolver__generic_relation(undine_settings) -> None:
    undine_settings.ASYNC = False

    commenter = PersonFactory.create()

    class TaskType(QueryType[Task]): ...

    class RelatedComment(MutationType[Comment], kind="related"):
        contents = Input()
        commenter = Input(Person)

    class TaskCreateMutation(MutationType[Task]):
        comments = Input(RelatedComment, many=True)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    class Query(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation, entrypoint=Query.bulk_create_tasks)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
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

    assert tasks[0].name == "Test task"
    assert list(tasks[0].comments.all()) == [comment]


@pytest.mark.django_db
def test_bulk_create_resolver__mutation_hooks(undine_settings) -> None:
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_bulk_create_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

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
        assert isawaitable(results)

        results = await results

    assert isinstance(results, list)
    assert len(results) == 2

    assert isinstance(results[0], Task)
    assert results[0].name == "Test task 1"
    assert results[0].type == TaskTypeChoices.STORY

    assert isinstance(results[1], Task)
    assert results[1].name == "Test task 2"
    assert results[1].type == TaskTypeChoices.BUG_FIX
