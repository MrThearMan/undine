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


class TeamCreateMutation(ModelGQLMutation, model=Team):
    name = Input()


class ProjectCreateMutation(ModelGQLMutation, model=Project):
    name = Input()
    team = Input(TeamCreateMutation)


class ServiceRequestCreateMutation(ModelGQLMutation, model=ServiceRequest):
    details = Input()


class PersonCreateMutation(ModelGQLMutation, model=Person):
    name = Input()


class TaskResultCreateMutation(ModelGQLMutation, model=TaskResult):
    details = Input()
    time_used = Input()


class TaskStepCreateMutation(ModelGQLMutation, model=TaskStep):
    name = Input()


class ReportCreateMutation(ModelGQLMutation, model=Report):
    name = Input()
    content = Input()


class CommentCreateMutation(ModelGQLMutation, model=Comment):
    contents = Input()
    commenter = Input(PersonCreateMutation)
    target = Input()


# TODO: How to determine mutation type: create, update, delete, or other?
class TaskCreateMutation(ModelGQLMutation, model=Task):
    """Create a task."""

    name = Input()
    type = Input()

    request = Input(ServiceRequestCreateMutation)
    project = Input(ProjectCreateMutation)
    assignees = Input(PersonCreateMutation, many=True)

    result = Input(TaskResultCreateMutation)
    steps = Input(TaskStepCreateMutation, many=True)
    reports = Input(ReportCreateMutation, many=True)

    comments = Input(CommentCreateMutation, many=True)

    related_tasks = Input("self", many=True)
