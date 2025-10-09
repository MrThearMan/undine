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
from undine.typing import GQLInfo


class TeamInput(MutationType[Team], kind="related"): ...


class ProjectInput(MutationType[Project], kind="related"):
    team = Input(TeamInput)


class ServiceRequestInput(MutationType[ServiceRequest], kind="related"): ...


class PersonInput(MutationType[Person], kind="related"): ...


class TaskResultInput(MutationType[TaskResult], kind="related"): ...


class TaskStepInput(MutationType[TaskStep], kind="related"): ...


class ReportInput(MutationType[Report], kind="related"): ...


class CommentInput(MutationType[Comment], kind="related"):
    commenter = Input(PersonInput)
    target = Input()


class TaskInput(MutationType[Task], kind="related"):
    request = Input(ServiceRequestInput)
    project = Input(ProjectInput)
    assignees = Input(PersonInput)

    result = Input(TaskResultInput)
    steps = Input(TaskStepInput)
    reports = Input(ReportInput)

    comments = Input(CommentInput)

    related_tasks = Input(lambda: TaskInput)


class CustomInput(TypedDict):
    name: str
    age: int


class TaskCreateMutationType(MutationType[Task]):
    """Create a task."""

    input_only = Input(bool, default_value=True)
    custom = Input(CustomInput)

    @Input
    def current_user(self, info: GQLInfo) -> int | None:
        return info.context.user.id

    request = Input(ServiceRequestInput)
    project = Input(ProjectInput)
    assignees = Input(PersonInput)

    result = Input(TaskResultInput)
    steps = Input(TaskStepInput)
    reports = Input(ReportInput)

    comments = Input(CommentInput)

    related_tasks = Input(TaskInput)

    @input_only.validate
    def validate_name(self, info: GQLInfo, value: bool) -> None:  # noqa: FBT001
        if value == "foo":
            msg = "Name must not be 'foo'"
            raise ValueError(msg)


class CommentCreateMutationType(MutationType[Comment]): ...
