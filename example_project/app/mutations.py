from __future__ import annotations

from typing import TypedDict

from example_project.app.models import (
    Comment,
    Person,
    Project,
    Report,
    ServiceRequest,
    Task,
    TaskResult,
    TaskStep,
    Team,
)
from undine import Input
from undine.mutation import MutationType


class TeamCreateMutationTypeInput(MutationType, model=Team): ...


class ProjectCreateMutationTypeInput(MutationType, model=Project):
    team = Input(TeamCreateMutationTypeInput)


class ServiceRequestCreateMutationTypeInput(MutationType, model=ServiceRequest): ...


class PersonCreateMutationTypeInput(MutationType, model=Person): ...


class TaskResultCreateMutationTypeInput(MutationType, model=TaskResult): ...


class TaskStepCreateMutationTypeInput(MutationType, model=TaskStep): ...


class ReportCreateMutationTypeInput(MutationType, model=Report): ...


class CommentCreateMutationTypeInput(MutationType, model=Comment):
    commenter = Input(PersonCreateMutationTypeInput)
    target = Input()


class TaskCreateMutationTypeInput(MutationType, model=Task):
    request = Input(ServiceRequestCreateMutationTypeInput)
    project = Input(ProjectCreateMutationTypeInput)
    assignees = Input(PersonCreateMutationTypeInput)

    result = Input(TaskResultCreateMutationTypeInput)
    steps = Input(TaskStepCreateMutationTypeInput)
    reports = Input(ReportCreateMutationTypeInput)

    comments = Input(CommentCreateMutationTypeInput)

    related_tasks = Input("self")


class CustomInput(TypedDict):
    name: str
    age: int


class TaskCreateMutationType(MutationType, model=Task):
    """Create a task."""

    input_only = Input(bool)
    custom = Input(CustomInput)

    request = Input(ServiceRequestCreateMutationTypeInput)
    project = Input(ProjectCreateMutationTypeInput)
    assignees = Input(PersonCreateMutationTypeInput)

    result = Input(TaskResultCreateMutationTypeInput)
    steps = Input(TaskStepCreateMutationTypeInput)
    reports = Input(ReportCreateMutationTypeInput)

    comments = Input(CommentCreateMutationTypeInput)

    related_tasks = Input(TaskCreateMutationTypeInput)

    @input_only.validator
    def validate_name(self: Input, value: bool) -> None:  # noqa: FBT001
        if value == "foo":
            msg = "Name must not be 'foo'"
            raise ValueError(msg)
