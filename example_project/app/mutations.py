from __future__ import annotations

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


class TeamCreateMutation(ModelGQLMutation, model=Team): ...


class ProjectCreateMutation(ModelGQLMutation, model=Project):
    team = Input(TeamCreateMutation)


class ServiceRequestCreateMutation(ModelGQLMutation, model=ServiceRequest): ...


class PersonCreateMutation(ModelGQLMutation, model=Person): ...


class TaskResultCreateMutation(ModelGQLMutation, model=TaskResult): ...


class TaskStepCreateMutation(ModelGQLMutation, model=TaskStep): ...


class ReportCreateMutation(ModelGQLMutation, model=Report): ...


class CommentCreateMutation(ModelGQLMutation, model=Comment):
    commenter = Input(PersonCreateMutation)
    target = Input()


class TaskCreateMutation(ModelGQLMutation, model=Task):
    """Create a task."""

    name = Input()
    type = Input()

    request = Input(ServiceRequestCreateMutation)
    project = Input(ProjectCreateMutation)
    assignees = Input(PersonCreateMutation)

    result = Input(TaskResultCreateMutation)
    steps = Input(TaskStepCreateMutation)
    reports = Input(ReportCreateMutation)

    comments = Input(CommentCreateMutation)

    related_tasks = Input("self")
