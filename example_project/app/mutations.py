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


class TeamMutation(ModelGQLMutation, model=Team): ...


class ProjectMutation(ModelGQLMutation, model=Project):
    team = Input(TeamMutation)


class ServiceRequestMutation(ModelGQLMutation, model=ServiceRequest): ...


class PersonMutation(ModelGQLMutation, model=Person): ...


class TaskResultMutation(ModelGQLMutation, model=TaskResult): ...


class TaskStepMutation(ModelGQLMutation, model=TaskStep): ...


class ReportMutation(ModelGQLMutation, model=Report): ...


class CommentMutation(ModelGQLMutation, model=Comment):
    commenter = Input(PersonMutation)
    target = Input()


class TaskMutation(ModelGQLMutation, model=Task):
    request = Input(ServiceRequestMutation)
    project = Input(ProjectMutation)
    assignees = Input(PersonMutation)

    result = Input(TaskResultMutation)
    steps = Input(TaskStepMutation)
    reports = Input(ReportMutation)

    comments = Input(CommentMutation)

    related_tasks = Input("self")


class TaskCreateMutation(ModelGQLMutation, model=Task):
    """Create a task."""

    request = Input(ServiceRequestMutation)
    project = Input(ProjectMutation)
    assignees = Input(PersonMutation)

    result = Input(TaskResultMutation)
    steps = Input(TaskStepMutation)
    reports = Input(ReportMutation)

    comments = Input(CommentMutation)

    related_tasks = Input(TaskMutation)
