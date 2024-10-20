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


class TeamMutationTypeInput(MutationType, model=Team): ...


class ProjectMutationTypeInput(MutationType, model=Project):
    team = Input(TeamMutationTypeInput)


class ServiceRequestMutationTypeInput(MutationType, model=ServiceRequest): ...


class PersonMutationTypeInput(MutationType, model=Person): ...


class TaskResultMutationTypeInput(MutationType, model=TaskResult): ...


class TaskStepMutationTypeInput(MutationType, model=TaskStep): ...


class ReportMutationTypeInput(MutationType, model=Report): ...


class CommentMutationTypeInput(MutationType, model=Comment):
    commenter = Input(PersonMutationTypeInput)
    target = Input()


class TaskMutationTypeInput(MutationType, model=Task):
    request = Input(ServiceRequestMutationTypeInput)
    project = Input(ProjectMutationTypeInput)
    assignees = Input(PersonMutationTypeInput)

    result = Input(TaskResultMutationTypeInput)
    steps = Input(TaskStepMutationTypeInput)
    reports = Input(ReportMutationTypeInput)

    comments = Input(CommentMutationTypeInput)

    related_tasks = Input("self")


class CustomInput(TypedDict):
    name: str
    age: int


class TaskCreateMutationType(MutationType, model=Task):
    """Create a task."""

    input_only = Input(bool)
    custom = Input(CustomInput)

    request = Input(ServiceRequestMutationTypeInput)
    project = Input(ProjectMutationTypeInput)
    assignees = Input(PersonMutationTypeInput)

    result = Input(TaskResultMutationTypeInput)
    steps = Input(TaskStepMutationTypeInput)
    reports = Input(ReportMutationTypeInput)

    comments = Input(CommentMutationTypeInput)

    related_tasks = Input(TaskMutationTypeInput)

    @input_only.validator
    @staticmethod
    def _(value: bool) -> None:  # noqa: FBT001
        if value == "foo":
            msg = "Name must not be 'foo'"
            raise ValueError(msg)
