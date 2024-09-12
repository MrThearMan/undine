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
from undine import ModelGQLMutation
from undine.fields import Input


class TeamMutationInput(ModelGQLMutation, model=Team): ...


class ProjectMutationInput(ModelGQLMutation, model=Project):
    team = Input(TeamMutationInput)


class ServiceRequestMutationInput(ModelGQLMutation, model=ServiceRequest): ...


class PersonMutationInput(ModelGQLMutation, model=Person): ...


class TaskResultMutationInput(ModelGQLMutation, model=TaskResult): ...


class TaskStepMutationInput(ModelGQLMutation, model=TaskStep): ...


class ReportMutationInput(ModelGQLMutation, model=Report): ...


class CommentMutationInput(ModelGQLMutation, model=Comment):
    commenter = Input(PersonMutationInput)
    target = Input()


class TaskMutationInput(ModelGQLMutation, model=Task):
    request = Input(ServiceRequestMutationInput)
    project = Input(ProjectMutationInput)
    assignees = Input(PersonMutationInput)

    result = Input(TaskResultMutationInput)
    steps = Input(TaskStepMutationInput)
    reports = Input(ReportMutationInput)

    comments = Input(CommentMutationInput)

    related_tasks = Input("self")


class CustomInput(TypedDict):
    name: str
    age: int


class TaskCreateMutation(ModelGQLMutation, model=Task):
    """Create a task."""

    input_only = Input(bool)
    custom = Input(CustomInput)

    request = Input(ServiceRequestMutationInput)
    project = Input(ProjectMutationInput)
    assignees = Input(PersonMutationInput)

    result = Input(TaskResultMutationInput)
    steps = Input(TaskStepMutationInput)
    reports = Input(ReportMutationInput)

    comments = Input(CommentMutationInput)

    related_tasks = Input(TaskMutationInput)
