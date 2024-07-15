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


class ProjectTeamMutationInput(ModelGQLMutation, model=Team):
    name = Input()


class TaskProjectMutationInput(ModelGQLMutation, model=Project):
    name = Input()
    team = Input(ProjectTeamMutationInput)


class TaskServiceRequestMutationInput(ModelGQLMutation, model=ServiceRequest):
    details = Input()


class TaskPersonMutationInput(ModelGQLMutation, model=Person):
    name = Input()


class TaskResultMutationInput(ModelGQLMutation, model=TaskResult):
    details = Input()
    time_used = Input()


class TaskStepMutationInput(ModelGQLMutation, model=TaskStep):
    name = Input()


class TaskReportInput(ModelGQLMutation, model=Report):
    name = Input()
    content = Input()


class TaskCommentInput(ModelGQLMutation, model=Comment):
    contents = Input()
    commenter = Input(TaskPersonMutationInput)
    target = Input()


class TaskCreateMutation(ModelGQLMutation, model=Task):
    """Create a task."""

    name = Input()
    type = Input()

    request = Input(TaskServiceRequestMutationInput)
    project = Input(TaskProjectMutationInput)
    assignees = Input(TaskPersonMutationInput, many=True)

    result = Input(TaskResultMutationInput)
    steps = Input(TaskStepMutationInput, many=True)
    reports = Input(TaskReportInput, many=True)

    comments = Input(TaskCommentInput, many=True)

    related_tasks = Input("self", many=True)
