from __future__ import annotations

import copy
from typing import Any

import pytest
from asgiref.sync import sync_to_async
from graphql.pyutils import Path

from example_project.app.models import Person, Project, Task, TaskTypeChoices, Team
from tests.factories import PersonFactory, ProjectFactory, TeamFactory
from tests.helpers import mock_gql_info
from undine import GQLInfo, Input, MutationType
from undine.exceptions import (
    GraphQLErrorGroup,
    GraphQLModelNotFoundError,
    GraphQLPermissionError,
    GraphQLValidationError,
)
from undine.utils.pre_mutation import pre_mutation, pre_mutation_async, pre_mutation_many, pre_mutation_many_async

# Sync


def test_pre_mutation() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    pre_mutation(instance=instance, info=mock_info, input_data=input_data, mutation_type=TaskCreateMutation)

    assert input_data == {"name": "Test task"}


def test_pre_mutation_many() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    pre_mutation_many(instances=[instance], info=mock_info, input_data=[input_data], mutation_type=TaskCreateMutation)

    assert input_data == {"name": "Test task"}


@pytest.mark.django_db
def test_pre_mutation__model_input() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(Project)

    project = ProjectFactory.create()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "project": project.pk}

    pre_mutation(instance=instance, info=mock_info, input_data=input_data, mutation_type=TaskCreateMutation)

    assert input_data["project"] == project


@pytest.mark.django_db
def test_pre_mutation__model_input__many() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        assignees = Input(Person, many=True)

    person = PersonFactory.create()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "assignees": [person.pk]}

    pre_mutation(instance=instance, info=mock_info, input_data=input_data, mutation_type=TaskCreateMutation)

    assert input_data["assignees"] == [person]


@pytest.mark.django_db
def test_pre_mutation__model_input__none() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(Project)

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "project": None}

    pre_mutation(instance=instance, info=mock_info, input_data=input_data, mutation_type=TaskCreateMutation)

    assert input_data["project"] is None


@pytest.mark.django_db
def test_pre_mutation__model_input__not_found() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(Project)

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "project": 1}

    with pytest.raises(GraphQLModelNotFoundError) as exc_info:
        pre_mutation(instance=instance, info=mock_info, input_data=input_data, mutation_type=TaskCreateMutation)

    assert exc_info.value.path == ["task", "project"]


def test_pre_mutation__hidden_input() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @Input(hidden=True)
        def done(self, info: GQLInfo) -> bool:
            return False

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    pre_mutation(instance=instance, info=mock_info, input_data=input_data, mutation_type=TaskCreateMutation)

    assert input_data["done"] is False


def test_pre_mutation__hidden_input__default_value() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        done = Input(bool, hidden=True, default_value=False)

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    pre_mutation(instance=instance, info=mock_info, input_data=input_data, mutation_type=TaskCreateMutation)

    assert input_data["done"] is False


def test_pre_mutation__function_input() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        @Input
        def name(self, info: GQLInfo, value: str) -> str:
            return value.upper()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    pre_mutation(instance=instance, info=mock_info, input_data=input_data, mutation_type=TaskCreateMutation)

    assert input_data["name"] == "TEST TASK"


def test_pre_mutation__permissions() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLPermissionError) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    assert exc_info.value.path == ["task"]


def test_pre_mutation__permissions__field__single() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "name"]


def test_pre_mutation__permissions__field__multiple() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            msg = "Invalid name"
            raise GraphQLPermissionError(msg)

        @type.permissions
        def type_permissions(self, info: GQLInfo, value: TaskTypeChoices) -> None:
            msg = "Invalid type"
            raise GraphQLPermissionError(msg)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "type": TaskTypeChoices.STORY}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 2

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].message == "Invalid name"
    assert errors[0].path == ["task", "name"]

    assert isinstance(errors[1], GraphQLPermissionError)
    assert errors[1].message == "Invalid type"
    assert errors[1].path == ["task", "type"]


def test_pre_mutation__validate() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLValidationError) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    assert exc_info.value.path == ["task"]


def test_pre_mutation__validate__field() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @name.validate
        def name_validate(self, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLValidationError)
    assert errors[0].path == ["task", "name"]


def test_pre_mutation__validate__field__multiple() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.validate
        def name_validate(self, info: GQLInfo, value: str) -> None:
            msg = "Invalid name"
            raise GraphQLValidationError(msg)

        @type.validate
        def type_validate(self, info: GQLInfo, value: TaskTypeChoices) -> None:
            msg = "Invalid type"
            raise GraphQLValidationError(msg)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "type": TaskTypeChoices.STORY}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 2

    assert isinstance(errors[0], GraphQLValidationError)
    assert errors[0].message == "Invalid name"
    assert errors[0].path == ["task", "name"]

    assert isinstance(errors[1], GraphQLValidationError)
    assert errors[1].message == "Invalid type"
    assert errors[1].path == ["task", "type"]


def test_pre_mutation__input_only_inputs() -> None:
    input_only_data = None

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        foo = Input(str, input_only=True)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal input_only_data
            input_only_data = copy.deepcopy(input_data)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "foo": "bar"}

    pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    assert data == {"name": "Test task"}
    assert input_only_data == {"name": "Test task", "foo": "bar"}


# Sync - related


@pytest.mark.django_db
def test_pre_mutation__related_mutation_type__model_input() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()
        team = Input(Team)

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    team = TeamFactory.create()

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test project", "team": team.pk}}

    pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    assert data["project"] == {"name": "Test project", "team": team}


@pytest.mark.django_db
def test_pre_mutation__related_mutation_type__model_input__null() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()
        team = Input(Team)

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test project", "team": None}}

    pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    assert data["project"] == {"name": "Test project", "team": None}


@pytest.mark.django_db
def test_pre_mutation__related_mutation_type__model_input__not_found() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()
        team = Input(Team)

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test project", "team": 1}}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLModelNotFoundError)
    assert errors[0].path == ["task", "project", "team"]


def test_pre_mutation__related_mutation_type__hidden_input() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        pk = Input(int, required=True)

        @Input(hidden=True)
        def name(self, info: GQLInfo) -> str:
            return "foo"

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"pk": 1}}

    pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    assert data["project"] == {"pk": 1, "name": "foo"}


def test_pre_mutation__related_mutation_type__hidden_input__default_value() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        pk = Input(int, required=True)
        name = Input(str, hidden=True, default_value="foo")

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"pk": 1}}

    pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    assert data["project"] == {"pk": 1, "name": "foo"}


def test_pre_mutation__related_mutation_type__function_input() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        @Input
        def name(self, info: GQLInfo, value: str) -> str:
            return value.upper()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test task"}}

    pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    assert data["project"] == {"name": "TEST TASK"}


def test_pre_mutation__related_mutation_type__permissions() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()

        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test task"}}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "project"]


def test_pre_mutation__related_mutation_type__permissions__field__single() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test task"}}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "project", "name"]


def test_pre_mutation__related_mutation_type__permissions__field__multiple() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()
        team = Input(int)

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

        @team.permissions
        def team_permissions(self, info: GQLInfo, value: int) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test task", "team": 1}}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 2

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "project", "name"]

    assert isinstance(errors[1], GraphQLPermissionError)
    assert errors[1].path == ["task", "project", "team"]


def test_pre_mutation__related_mutation_type__validate() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()

        @classmethod
        def __validate__(cls, instance: Project, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test task"}}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLValidationError)
    assert errors[0].path == ["task", "project"]


def test_pre_mutation__related_mutation_type__validate__field__single() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test task"}}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "project", "name"]


def test_pre_mutation__related_mutation_type__validate__field__multiple() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()
        team = Input(int)

        @name.validate
        def name_validate(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

        @team.validate
        def team_validate(self, info: GQLInfo, value: int) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))

    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test task", "team": 1}}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        pre_mutation(instance=inst, info=mock_info, input_data=data, mutation_type=TaskCreateMutation)

    errors = list(exc_info.value.flatten())
    assert len(errors) == 2

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "project", "name"]

    assert isinstance(errors[1], GraphQLPermissionError)
    assert errors[1].path == ["task", "project", "team"]


# Async


@pytest.mark.asyncio
async def test_pre_mutation_async() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )


@pytest.mark.asyncio
async def test_pre_mutation_many_async() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    await pre_mutation_many_async(
        instances=[instance],
        info=mock_info,
        input_data=[input_data],
        mutation_type=TaskCreateMutation,
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_pre_mutation_async__model_input() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(Project)

    project = await sync_to_async(ProjectFactory.create)()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "project": project.pk}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data["project"] == project


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_pre_mutation_async__model_input__many() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        assignees = Input(Person, many=True)

    person = await sync_to_async(PersonFactory.create)()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "assignees": [person.pk]}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data["assignees"] == [person]


@pytest.mark.asyncio
async def test_pre_mutation_async__model_input__null() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(Project)

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "project": None}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data["project"] is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_pre_mutation_async__model_input__not_found() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(Project)

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "project": 1}

    with pytest.raises(GraphQLModelNotFoundError) as exc_info:
        await pre_mutation_async(
            instance=instance,
            info=mock_info,
            input_data=input_data,
            mutation_type=TaskCreateMutation,
        )

    assert exc_info.value.path == ["task", "project"]


@pytest.mark.asyncio
async def test_pre_mutation_async__hidden_input() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @Input(hidden=True)
        def done(self, info: GQLInfo) -> bool:
            return False

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data["done"] is False


@pytest.mark.asyncio
async def test_pre_mutation_async__hidden_input__async() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @Input(hidden=True)
        async def done(self, info: GQLInfo) -> bool:
            return False

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data["done"] is False


@pytest.mark.asyncio
async def test_pre_mutation_async__hidden_input__default_value() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        done = Input(bool, hidden=True, default_value=False)

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data["done"] is False


@pytest.mark.asyncio
async def test_pre_mutation_async__function_input() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        @Input
        def name(self, info: GQLInfo, value: str) -> str:
            return value.upper()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data["name"] == "TEST TASK"


@pytest.mark.asyncio
async def test_pre_mutation_async__function_input__coroutine() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        @Input
        async def name(self, info: GQLInfo, value: str) -> str:
            return value.upper()

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task"}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data["name"] == "TEST TASK"


@pytest.mark.asyncio
async def test_pre_mutation_async__permissions() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLPermissionError) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    assert exc_info.value.path == ["task"]


@pytest.mark.asyncio
async def test_pre_mutation_async__permissions__async() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLPermissionError) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    assert exc_info.value.path == ["task"]


@pytest.mark.asyncio
async def test_pre_mutation_async__permissions__field__single() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "name"]


@pytest.mark.asyncio
async def test_pre_mutation_async__permissions__field__multiple() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

        @type.permissions
        def type_permissions(self, info: GQLInfo, value: TaskTypeChoices) -> None:
            raise GraphQLPermissionError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "type": TaskTypeChoices.STORY}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    errors = list(exc_info.value.flatten())
    assert len(errors) == 2

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "name"]

    assert isinstance(errors[1], GraphQLPermissionError)
    assert errors[1].path == ["task", "type"]


@pytest.mark.asyncio
async def test_pre_mutation_async__permissions__field__async() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @name.permissions
        async def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLPermissionError)
    assert errors[0].path == ["task", "name"]


@pytest.mark.asyncio
async def test_pre_mutation_async__validate() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLValidationError) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    assert exc_info.value.path == ["task"]


@pytest.mark.asyncio
async def test_pre_mutation_async__validate__async() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @classmethod
        async def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLValidationError) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    assert exc_info.value.path == ["task"]


@pytest.mark.asyncio
async def test_pre_mutation_async__validate__field__single() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @name.validate
        def name_validate(self, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLValidationError)
    assert errors[0].path == ["task", "name"]


@pytest.mark.asyncio
async def test_pre_mutation_async__validate__field__multiple() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.validate
        def name_validate(self, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

        @type.validate
        def type_validate(self, info: GQLInfo, value: TaskTypeChoices) -> None:
            raise GraphQLValidationError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "type": TaskTypeChoices.STORY}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    errors = list(exc_info.value.flatten())
    assert len(errors) == 2

    assert isinstance(errors[0], GraphQLValidationError)
    assert errors[0].path == ["task", "name"]

    assert isinstance(errors[1], GraphQLValidationError)
    assert errors[1].path == ["task", "type"]


@pytest.mark.asyncio
async def test_pre_mutation_async__validate__field__async() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @name.validate
        async def name_validate(self, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task"}

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        await pre_mutation_async(
            instance=inst,
            info=mock_info,
            input_data=data,
            mutation_type=TaskCreateMutation,
        )

    errors = list(exc_info.value.flatten())
    assert len(errors) == 1

    assert isinstance(errors[0], GraphQLValidationError)
    assert errors[0].path == ["task", "name"]


@pytest.mark.asyncio
async def test_pre_mutation_async__input_only_inputs() -> None:
    input_only_data = None

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        foo = Input(str, input_only=True)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal input_only_data
            input_only_data = copy.deepcopy(input_data)

    instance = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    input_data: dict[str, Any] = {"name": "Test task", "foo": "bar"}

    await pre_mutation_async(
        instance=instance,
        info=mock_info,
        input_data=input_data,
        mutation_type=TaskCreateMutation,
    )

    assert input_data == {"name": "Test task"}
    assert input_only_data == {"name": "Test task", "foo": "bar"}


# Async - related


@pytest.mark.asyncio
async def test_pre_mutation_async__related_mutation_type() -> None:
    class RelatedProject(MutationType[Project], kind="related", auto=False):
        name = Input()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        project = Input(RelatedProject)

    inst = Task()
    mock_info = mock_gql_info(path=Path(prev=None, key="task", typename=None))
    data: dict[str, Any] = {"name": "Test task", "project": {"name": "Test project"}}

    await pre_mutation_async(
        instance=inst,
        info=mock_info,
        input_data=data,
        mutation_type=TaskCreateMutation,
    )
