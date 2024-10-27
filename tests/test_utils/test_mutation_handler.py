import datetime

import pytest

from example_project.app.models import Comment, Task, TaskObjective, TaskResult, TaskTypeChoices
from tests.factories import (
    CommentFactory,
    PersonFactory,
    ProjectFactory,
    ReportFactory,
    ServiceRequestFactory,
    TaskFactory,
    TaskObjectiveFactory,
    TaskResultFactory,
    TaskStepFactory,
)
from tests.helpers import exact
from undine.errors.exceptions import GraphQLInvalidInputDataError
from undine.utils.mutation_handler import MutationHandler

pytestmark = [
    pytest.mark.django_db,
]


def test_mutation_handler__create():
    data = {
        "name": "Test task",
        "type": TaskTypeChoices.TASK.value,
        "request": {
            "details": "Test request",
            "submitted_at": "2024-01-01",
        },
        "project": {
            "name": "Test project",
            "team": {
                "name": "Test team",
            },
        },
        "assignees": [
            {
                "name": "Test user",
                "email": "test@user.com",
            },
        ],
        "result": {
            "details": "Test result",
            "time_used": datetime.timedelta(seconds=1),
        },
        "steps": [
            {
                "name": "Test step",
            },
        ],
        "reports": [
            {
                "name": "Test report",
                "content": "Test report content",
            },
        ],
        "comments": [
            {
                "contents": "Test comment",
                "commenter": {
                    "name": "Test commenter",
                    "email": "test@commenter.com",
                },
            },
        ],
        "relatedTasks": [
            {
                "name": "Related task",
                "type": TaskTypeChoices.BUG_FIX.value,
                "request": {
                    "details": "Related request",
                    "submitted_at": "2024-01-02",
                },
                "project": {
                    "name": "Related project",
                    "team": {
                        "name": "Related team",
                    },
                },
            },
        ],
    }

    handler = MutationHandler[Task](model=Task)
    instance = handler.create(data)

    assert instance.name == "Test task"
    assert instance.type == TaskTypeChoices.TASK

    assert instance.request.details == "Test request"

    assert instance.project.name == "Test project"
    assert instance.project.team.name == "Test team"

    assert instance.assignees.count() == 1
    assert instance.assignees.first().name == "Test user"

    assert instance.result.details == "Test result"
    assert instance.result.time_used == datetime.timedelta(seconds=1)

    assert instance.steps.count() == 1
    assert instance.steps.first().name == "Test step"

    assert instance.reports.count() == 1
    assert instance.reports.first().name == "Test report"
    assert instance.reports.first().content == "Test report content"

    assert instance.comments.count() == 1
    assert instance.comments.first().contents == "Test comment"
    assert instance.comments.first().commenter.name == "Test commenter"

    assert instance.related_tasks.count() == 1
    assert instance.related_tasks.first().name == "Related task"
    assert instance.related_tasks.first().request.details == "Related request"
    assert instance.related_tasks.first().project.name == "Related project"
    assert instance.related_tasks.first().project.team.name == "Related team"


def test_mutation_handler__update__retain_relations():
    task = TaskFactory.create(
        name="Task",
        request__details="Request",
        project__name="Project",
        project__team__name="Team",
        assignees__name="Assignee",
        result__details="Result",
        objective__details="Objective",
        steps__name="Step",
        acceptancecriteria_set__details="Criteria",
        reports__name="Report",
        comments__contents="Comment",
        comments__commenter__name="Commenter",
        related_tasks__name="Related Task",
        related_tasks__request__details="Related Request",
        related_tasks__project__name="Related Project",
        related_tasks__project__team__name="Related Team",
    )

    request = task.request
    project = task.project
    team = project.team
    assignee = task.assignees.first()
    result = task.result
    objective = task.objective
    step = task.steps.first()
    report = task.reports.first()
    comment = task.comments.first()
    commenter = comment.commenter
    related_task = task.related_tasks.first()
    related_request = related_task.request
    related_project = related_task.project
    related_team = related_project.team

    data = {
        "name": "New Task",
        "request": {
            "pk": request.pk,
            "details": "New Request",
            "submitted_at": "2024-01-01",
        },
        "project": {
            "pk": project.pk,
            "name": "New Project",
            "team": {
                "pk": team.pk,
                "name": "New Team",
            },
        },
        "assignees": [
            {
                "pk": assignee.pk,
                "name": "New Assignee",
            },
        ],
        "result": {
            "pk": result.pk,
            "details": "New Result",
        },
        "objective": {
            "pk": objective.pk,
            "details": "New Objective",
        },
        "steps": [
            {
                "pk": step.pk,
                "name": "New Step",
            },
        ],
        "reports": [
            {
                "pk": report.pk,
                "name": "New Report",
            },
        ],
        "comments": [
            {
                "pk": comment.pk,
                "contents": "New Comment",
                "commenter": {
                    "pk": commenter.pk,
                    "name": "New Commenter",
                },
            },
        ],
        "relatedTasks": [
            {
                "pk": related_task.pk,
                "name": "New Related Task",
                "request": {
                    "pk": related_request.pk,
                    "details": "New Related Request",
                    "submitted_at": "2024-01-02",
                },
                "project": {
                    "pk": related_project.pk,
                    "name": "New Related Project",
                    "team": {
                        "pk": related_team.pk,
                        "name": "New Related Team",
                    },
                },
            },
        ],
    }

    handler = MutationHandler[Task](model=Task)
    instance = handler.update(task, data)

    instance.refresh_from_db()

    assert instance.pk == task.pk
    assert instance.name == "New Task"

    assert instance.request.pk == request.pk
    assert instance.request.details == "New Request"

    assert instance.project.pk == project.pk
    assert instance.project.name == "New Project"
    assert instance.project.team.pk == team.pk
    assert instance.project.team.name == "New Team"

    assert instance.assignees.count() == 1
    assert instance.assignees.first().pk == assignee.pk
    assert instance.assignees.first().name == "New Assignee"

    assert instance.result.pk == result.pk
    assert instance.result.details == "New Result"

    assert instance.objective.pk == result.pk
    assert instance.objective.details == "New Objective"

    assert instance.steps.count() == 1
    assert instance.steps.first().pk == step.pk
    assert instance.steps.first().name == "New Step"

    assert instance.reports.count() == 1
    assert instance.reports.first().pk == report.pk
    assert instance.reports.first().name == "New Report"

    assert instance.comments.count() == 1
    assert instance.comments.first().pk == comment.pk
    assert instance.comments.first().contents == "New Comment"
    assert instance.comments.first().commenter.pk == commenter.pk
    assert instance.comments.first().commenter.name == "New Commenter"

    assert instance.related_tasks.count() == 1
    assert instance.related_tasks.first().pk == related_task.pk
    assert instance.related_tasks.first().name == "New Related Task"
    assert instance.related_tasks.first().request.pk == related_request.pk
    assert instance.related_tasks.first().request.details == "New Related Request"
    assert instance.related_tasks.first().project.pk == related_project.pk
    assert instance.related_tasks.first().project.name == "New Related Project"
    assert instance.related_tasks.first().project.team.pk == related_team.pk
    assert instance.related_tasks.first().project.team.name == "New Related Team"


def test_mutation_handler__update__retain_relations__integers():
    task = TaskFactory.create(
        name="Task",
        request__details="Request",
        project__name="Project",
        project__team__name="Team",
        assignees__name="Assignee",
        assignees__email="assignee@example.com",
        result__details="Result",
        objective__details="Objective",
        steps__name="Step",
        acceptancecriteria_set__details="Criteria",
        reports__name="Report",
        comments__contents="Comment",
        comments__commenter__name="Commenter",
        comments__commenter__email="commenter@example.com",
        related_tasks__name="Related Task",
        related_tasks__request__details="Related Request",
        related_tasks__project__name="Related Project",
        related_tasks__project__team__name="Related Team",
    )

    request = task.request
    project = task.project
    team = project.team
    assignee = task.assignees.first()
    result = task.result
    objective = task.objective
    step = task.steps.first()
    report = task.reports.first()
    comment = task.comments.first()
    commenter = comment.commenter
    related_task = task.related_tasks.first()
    related_request = related_task.request
    related_project = related_task.project
    related_team = related_project.team

    data = {
        "name": "New Task",
        "request": request.pk,
        "project": project.pk,
        "assignees": [assignee.pk],
        "result": result.pk,
        "objective": objective.pk,
        "steps": [step.pk],
        "reports": [report.pk],
        "comments": [comment.pk],
        "relatedTasks": [related_task.pk],
    }

    handler = MutationHandler[Task](model=Task)
    instance = handler.update(task, data)

    instance.refresh_from_db()

    assert instance.pk == task.pk
    assert instance.name == "New Task"

    assert instance.request.pk == request.pk
    assert instance.request.details == "Request"

    assert instance.project.pk == project.pk
    assert instance.project.name == "Project"
    assert instance.project.team.pk == team.pk
    assert instance.project.team.name == "Team"

    assert instance.assignees.count() == 1
    assert instance.assignees.first().pk == assignee.pk
    assert instance.assignees.first().name == "Assignee"

    assert instance.result.pk == result.pk
    assert instance.result.details == "Result"

    assert instance.objective.pk == result.pk
    assert instance.objective.details == "Objective"

    assert instance.steps.count() == 1
    assert instance.steps.first().pk == step.pk
    assert instance.steps.first().name == "Step"

    assert instance.reports.count() == 1
    assert instance.reports.first().pk == report.pk
    assert instance.reports.first().name == "Report"

    assert instance.comments.count() == 1
    assert instance.comments.first().pk == comment.pk
    assert instance.comments.first().contents == "Comment"
    assert instance.comments.first().commenter.pk == commenter.pk
    assert instance.comments.first().commenter.name == "Commenter"

    assert instance.related_tasks.count() == 1
    assert instance.related_tasks.first().pk == related_task.pk
    assert instance.related_tasks.first().name == "Related Task"
    assert instance.related_tasks.first().request.pk == related_request.pk
    assert instance.related_tasks.first().request.details == "Related Request"
    assert instance.related_tasks.first().project.pk == related_project.pk
    assert instance.related_tasks.first().project.name == "Related Project"
    assert instance.related_tasks.first().project.team.pk == related_team.pk
    assert instance.related_tasks.first().project.team.name == "Related Team"


def test_mutation_handler__update__new_relations():
    task = TaskFactory.create(
        name="Task",
        request__details="Request",
        project__name="Project",
        project__team__name="Team",
        assignees__name="Assignee",
        assignees__email="assignee@example.com",
        result__details="Result",
        objective__details="Objective",
        steps__name="Step",
        acceptancecriteria_set__details="Criteria",
        reports__name="Report",
        comments__contents="Comment",
        comments__commenter__name="Commenter",
        comments__commenter__email="commenter@example.com",
        related_tasks__name="Related Task",
        related_tasks__request__details="Related Request",
        related_tasks__project__name="Related Project",
        related_tasks__project__team__name="Related Team",
    )

    request = task.request
    project = task.project
    team = project.team
    assignee = task.assignees.first()
    result = task.result
    step = task.steps.first()
    report = task.reports.first()
    comment = task.comments.first()
    commenter = comment.commenter
    related_task = task.related_tasks.first()
    related_request = related_task.request
    related_project = related_task.project
    related_team = related_project.team

    data = {
        "name": "New Task",
        "request": {
            "details": "New Request",
            "submitted_at": "2024-01-01",
        },
        "project": {
            "name": "New Project",
            "team": {
                "name": "New Team",
            },
        },
        "assignees": [
            {
                "name": "New Assignee",
                "email": "new.assignee@example.com",
            },
        ],
        "result": {
            "details": "New Assignee",
            "time_used": result.time_used,
        },
        "steps": [
            {
                "name": "New Step",
            },
        ],
        "reports": [
            {
                "name": "New Report",
                "content": report.content,
            },
        ],
        "comments": [
            {
                "contents": "New Comment",
                "commenter": {
                    "name": "New Commenter",
                    "email": "new.commenter@example.com",
                },
            },
        ],
        "relatedTasks": [
            {
                "name": "New Related Task",
                "type": TaskTypeChoices.BUG_FIX.value,
                "request": {
                    "details": "New Related Request",
                    "submitted_at": "2024-01-02",
                },
                "project": {
                    "name": "New Related Project",
                    "team": {
                        "name": "New Related Team",
                    },
                },
            },
        ],
    }

    handler = MutationHandler[Task](model=Task)
    instance = handler.update(task, data)

    instance.refresh_from_db()

    assert instance.pk == task.pk
    assert instance.name == "New Task"

    assert instance.request.pk != request.pk
    assert instance.request.details == "New Request"

    assert instance.project.pk != project.pk
    assert instance.project.name == "New Project"
    assert instance.project.team.pk != team.pk
    assert instance.project.team.name == "New Team"

    assert instance.assignees.count() == 1
    assert instance.assignees.first().pk != assignee.pk
    assert instance.assignees.first().name == "New Assignee"

    assert instance.result.pk != result.pk
    assert instance.result.details == "New Assignee"

    assert instance.steps.count() == 1
    assert instance.steps.first().pk != step.pk
    assert instance.steps.first().name == "New Step"

    # Entities not in input data are removed.
    assert instance.reports.count() == 1
    assert instance.reports.first().pk != report.pk
    assert instance.reports.first().name == "New Report"

    assert instance.comments.count() == 1
    assert instance.comments.first().pk != comment.pk
    assert instance.comments.first().contents == "New Comment"
    assert instance.comments.first().commenter.pk != commenter.pk
    assert instance.comments.first().commenter.name == "New Commenter"

    assert instance.related_tasks.count() == 1
    assert instance.related_tasks.first().pk != related_task.pk
    assert instance.related_tasks.first().name == "New Related Task"
    assert instance.related_tasks.first().request.pk != related_request.pk
    assert instance.related_tasks.first().request.details == "New Related Request"
    assert instance.related_tasks.first().project.pk != related_project.pk
    assert instance.related_tasks.first().project.name == "New Related Project"
    assert instance.related_tasks.first().project.team.pk != related_team.pk
    assert instance.related_tasks.first().project.team.name == "New Related Team"


def test_mutation_handler__update__new_relations__integers():
    task = TaskFactory.create(
        name="Task",
        request__details="Request",
        project__name="Project",
        project__team__name="Team",
        assignees__name="Assignee",
        assignees__email="assignee@example.com",
        result__details="Result",
        objective__details="Objective",
        steps__name="Step",
        acceptancecriteria_set__details="Criteria",
        reports__name="Report",
        comments__contents="Comment",
        comments__commenter__name="Commenter",
        comments__commenter__email="commenter@example.com",
        related_tasks__name="Related Task",
        related_tasks__request__details="Related Request",
        related_tasks__project__name="Related Project",
        related_tasks__project__team__name="Related Team",
    )

    new_request = ServiceRequestFactory.create(details="New Request")
    new_project = ProjectFactory.create(name="New Project")
    new_assignee = PersonFactory.create(name="New Assignee")
    new_objective = TaskObjectiveFactory.create(details="New Objective")
    new_result = TaskResultFactory.create(details="New Result")
    new_step = TaskStepFactory.create(name="New Step")
    new_report = ReportFactory.create(name="New Report")
    new_related_task = TaskFactory.create(name="New Related Task")
    new_comment = CommentFactory.create(contents="New Comment", target=new_related_task)

    data = {
        "name": "New Task",
        "request": new_request.pk,
        "project": new_project.pk,
        "assignees": [new_assignee.pk],
        "result": new_result.pk,
        "objective": new_objective.pk,
        "steps": [new_step.pk],
        "reports": [new_report.pk],
        "comments": [new_comment.pk],
        "relatedTasks": [new_related_task.pk],
    }

    handler = MutationHandler[Task](model=Task)
    instance = handler.update(task, data)

    instance.refresh_from_db()

    assert instance.request.pk == new_request.pk
    assert instance.project.pk == new_project.pk
    assert instance.assignees.count() == 1
    assert instance.assignees.first().pk == new_assignee.pk

    assert instance.result.pk == new_result.pk
    assert TaskResult.objects.count() == 1  # Non-nullable relation removed.
    assert instance.objective.pk == new_objective.pk
    assert TaskObjective.objects.count() == 2  # Nullable relation is retained.

    assert instance.steps.count() == 1
    assert instance.steps.first().pk == new_step.pk

    # Entities not in input data are removed.
    assert instance.reports.count() == 1
    assert instance.reports.first().pk == new_report.pk

    assert instance.comments.count() == 1
    assert instance.comments.first().pk == new_comment.pk

    assert instance.related_tasks.count() == 1
    assert instance.related_tasks.first().pk == new_related_task.pk


def test_mutation_handler__update__empty():
    task = TaskFactory.create(
        name="Task",
        request__details="Request",
        project__name="Project",
        project__team__name="Team",
        assignees__name="Assignee",
        result__details="Result",
        objective__details="Objective",
        steps__name="Step",
        acceptancecriteria_set__details="Criteria",
        reports__name="Report",
        comments__contents="Comment",
        comments__commenter__name="Commenter",
        related_tasks__name="Related Task",
        related_tasks__request__details="Related Request",
        related_tasks__project__name="Related Project",
        related_tasks__project__team__name="Related Team",
    )

    data = {
        "name": "New Task",
        "request": None,
        "project": None,
        "assignees": [],
        "result": None,
        "objective": None,
        "steps": [],
        "reports": [],
        "comments": [],
        "relatedTasks": [],
    }

    handler = MutationHandler[Task](model=Task)
    instance = handler.update(task, data)

    instance.refresh_from_db()

    assert instance.pk == task.pk
    assert instance.name == "New Task"

    assert instance.request is None
    assert instance.project is None
    assert instance.assignees.count() == 0
    assert not hasattr(instance, "result")
    assert TaskResult.objects.count() == 0  # Non-nullable relation removed.
    assert not hasattr(instance, "objective")
    assert TaskObjective.objects.count() == 1  # Nullable relation remains.
    assert instance.steps.count() == 0
    assert instance.reports.count() == 0
    assert instance.comments.count() == 0
    assert instance.related_tasks.count() == 0


def test_mutation_handler__update__no_related_input_data():
    task = TaskFactory.create(
        name="Task",
        request__details="Request",
        project__name="Project",
        project__team__name="Team",
        assignees__name="Assignee",
        result__details="Result",
        steps__name="Step",
        acceptancecriteria_set__details="Criteria",
        reports__name="Report",
        comments__contents="Comment",
        comments__commenter__name="Commenter",
        related_tasks__name="Related Task",
        related_tasks__request__details="Related Request",
        related_tasks__project__name="Related Project",
        related_tasks__project__team__name="Related Team",
    )

    request = task.request
    project = task.project
    team = project.team
    assignee = task.assignees.first()
    result = task.result
    step = task.steps.first()
    report = task.reports.first()
    comment = task.comments.first()
    commenter = comment.commenter
    related_task = task.related_tasks.first()
    related_request = related_task.request
    related_project = related_task.project
    related_team = related_project.team

    data = {
        "request": {
            "pk": request.pk,
        },
        "project": {
            "pk": project.pk,
            "team": {
                "pk": team.pk,
            },
        },
        "assignees": [
            {
                "pk": assignee.pk,
            },
        ],
        "result": {
            "pk": result.pk,
        },
        "steps": [
            {
                "pk": step.pk,
            },
        ],
        "reports": [
            {
                "pk": report.pk,
            },
        ],
        "comments": [
            {
                "pk": comment.pk,
                "commenter": {
                    "pk": commenter.pk,
                },
            },
        ],
        "relatedTasks": [
            {
                "pk": related_task.pk,
                "request": {
                    "pk": related_request.pk,
                },
                "project": {
                    "pk": related_project.pk,
                    "team": {
                        "pk": related_team.pk,
                    },
                },
            },
        ],
    }

    handler = MutationHandler[Task](model=Task)
    instance = handler.update(task, data)

    instance.refresh_from_db()

    assert instance.pk == task.pk

    assert instance.request.pk == request.pk

    assert instance.project.pk == project.pk
    assert instance.project.team.pk == team.pk

    assert instance.assignees.count() == 1
    assert instance.assignees.first().pk == assignee.pk

    assert instance.result.pk == result.pk

    assert instance.steps.count() == 1
    assert instance.steps.first().pk == step.pk

    assert instance.reports.count() == 1
    assert instance.reports.first().pk == report.pk

    assert instance.comments.count() == 1
    assert instance.comments.first().pk == comment.pk
    assert instance.comments.first().commenter.pk == commenter.pk

    assert instance.related_tasks.count() == 1
    assert instance.related_tasks.first().pk == related_task.pk
    assert instance.related_tasks.first().request.pk == related_request.pk
    assert instance.related_tasks.first().project.pk == related_project.pk
    assert instance.related_tasks.first().project.team.pk == related_team.pk


def test_mutation_handler__update__reverse_one_to_one__added_when_null():
    task = TaskFactory.create(name="Task 1")
    objective = TaskObjectiveFactory.create(details="Objective")

    assert getattr(task, "objective", None) is None

    data = {
        "objective": {
            "pk": objective.pk,
        },
    }

    handler = MutationHandler[Task](model=Task)
    handler.update(task, data)

    task.refresh_from_db()

    assert getattr(task, "objective", None) == objective


def test_mutation_handler__update__reverse_one_to_one__remove_existing__nullable():
    task = TaskFactory.create(
        name="Task 1",
        objective__details="Objective",
    )

    assert getattr(task, "objective", None) is not None

    data = {
        "objective": None,
    }

    handler = MutationHandler[Task](model=Task)
    handler.update(task, data)

    task.refresh_from_db()

    assert getattr(task, "objective", None) is None

    assert TaskObjective.objects.count() == 1


def test_mutation_handler__update__reverse_one_to_one__remove_existing__non_nullable():
    task = TaskFactory.create(
        name="Task 1",
        result__details="Result",
    )

    assert getattr(task, "result", None) is not None

    data = {
        "result": None,
    }

    handler = MutationHandler[Task](model=Task)
    handler.update(task, data)

    task.refresh_from_db()

    assert getattr(task, "objective", None) is None

    assert TaskResult.objects.count() == 0


def test_mutation_handler__update__reverse_one_to_one__replace_with_another_instance__nullable():
    task = TaskFactory.create(
        name="Task 1",
        objective__details="Objective 1",
    )

    new_objective = TaskObjectiveFactory.create(details="Objective 2")
    old_objective = task.objective

    data = {
        "objective": {
            "pk": new_objective.pk,
        },
    }

    handler = MutationHandler[Task](model=Task)
    handler.update(task, data)

    task.refresh_from_db()

    assert task.objective == new_objective

    assert TaskObjective.objects.filter(pk=old_objective.pk).exists() is True


def test_mutation_handler__update__reverse_one_to_one__replace_with_another_instance__non_nullable():
    task = TaskFactory.create(
        name="Task 1",
        result__details="Result",
    )

    old_result = task.result

    data = {
        "result": {
            "details": "Objective 2",
            "time_used": old_result.time_used,
        },
    }

    handler = MutationHandler[Task](model=Task)
    handler.update(task, data)

    task.refresh_from_db()

    assert task.result.pk != old_result.pk
    assert task.result.details == "Objective 2"

    assert TaskResult.objects.filter(pk=old_result.pk).exists() is False


def test_mutation_handler__update__reverse_one_to_one__replace_with_another_instance__integer():
    task = TaskFactory.create(
        name="Task 1",
        objective__details="Objective 1",
    )

    new_objective = TaskObjectiveFactory.create(details="Objective 2")
    old_objective = task.objective

    data = {
        "objective": new_objective.pk,
    }

    handler = MutationHandler[Task](model=Task)
    handler.update(task, data)

    task.refresh_from_db()

    assert task.objective == new_objective

    assert TaskObjective.objects.filter(pk=old_objective.pk).exists()


def test_mutation_handler__update__reverse_one_to_one__set_null_when_null_already():
    task = TaskFactory.create(name="Task 1")

    assert getattr(task, "objective", None) is None

    data = {
        "objective": None,
    }

    handler = MutationHandler[Task](model=Task)
    handler.update(task, data)

    task.refresh_from_db()

    assert getattr(task, "objective", None) is None


def test_mutation_handler__update__many_to_many__added_to_another_instance():
    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    assignee = PersonFactory.create(name="Assignee", tasks=[task_2])

    task_1.refresh_from_db()
    task_2.refresh_from_db()
    assignee.refresh_from_db()

    assert task_1.assignees.count() == 0
    assert task_2.assignees.count() == 1
    assert assignee.tasks.count() == 1

    data = {
        "assignees": [
            {"pk": assignee.pk},
        ],
    }

    handler = MutationHandler[Task](model=Task)
    handler.update(task_1, data)

    task_1.refresh_from_db()
    task_2.refresh_from_db()
    assignee.refresh_from_db()

    assert task_1.assignees.count() == 1
    assert task_2.assignees.count() == 1
    assert assignee.tasks.count() == 2

    assert task_1.assignees.first().pk == assignee.pk
    assert task_2.assignees.first().pk == assignee.pk


def test_mutation_handler__generic_foreign_key():
    task = TaskFactory.create(name="Test task")

    data = {
        "contents": "Test comment",
        "commenter": {
            "name": "Test commenter",
            "email": "test@commenter.com",
        },
        "target": {
            "typename": "Task",
            "pk": str(task.pk),
        },
    }

    handler = MutationHandler[Comment](model=Comment)
    instance = handler.create(data)

    assert instance.contents == "Test comment"
    assert instance.commenter.name == "Test commenter"
    assert instance.commenter.email == "test@commenter.com"

    assert isinstance(instance.target, Task)
    assert instance.target.name == "Test task"


def test_mutation_handler__generic_foreign_key__not_dict():
    data = {
        "contents": "Test comment",
        "commenter": {
            "name": "Test commenter",
            "email": "test@commenter.com",
        },
        "target": None,
    }

    handler = MutationHandler[Comment](model=Comment)

    msg = "Invalid input data for field 'target': None"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.create(data)


def test_mutation_handler__generic_foreign_key__missing_typename():
    data = {
        "contents": "Test comment",
        "commenter": {
            "name": "Test commenter",
            "email": "test@commenter.com",
        },
        "target": {
            "pk": 1,
        },
    }

    handler = MutationHandler[Comment](model=Comment)

    msg = "Missing 'typename' field in input data for field 'target'."
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.create(data)


def test_mutation_handler__generic_foreign_key__missing_pk():
    data = {
        "contents": "Test comment",
        "commenter": {
            "name": "Test commenter",
            "email": "test@commenter.com",
        },
        "target": {
            "typename": "Task",
        },
    }

    handler = MutationHandler[Comment](model=Comment)

    msg = "Missing 'pk' field in input data for field 'target'."
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.create(data)


def test_mutation_handler__generic_foreign_key__incorrect_model():
    task = TaskFactory.create(name="Test task")

    data = {
        "contents": "Test comment",
        "commenter": {
            "name": "Test commenter",
            "email": "test@commenter.com",
        },
        "target": {
            "typename": "Comment",
            "pk": str(task.pk),
        },
    }

    handler = MutationHandler[Comment](model=Comment)

    msg = "Field 'target' does not have a relation to a model named 'Comment'."
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.create(data)


def test_mutation_handler__invalid_type__reverse_one_to_one():
    task = TaskFactory.create(
        name="Task",
        objective__details="Objective",
    )

    data = {
        "objective": "foo",
    }

    handler = MutationHandler[Task](model=Task)

    msg = "Invalid input data for field 'objective': 'foo'"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.update(task, data)


def test_mutation_handler__invalid_type__one_to_many():
    task = TaskFactory.create(
        name="Task",
        steps__name="Step",
    )

    data = {
        "steps": "foo",
    }

    handler = MutationHandler[Task](model=Task)

    msg = "Invalid input data for field 'steps': 'foo'"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.update(task, data)


def test_mutation_handler__invalid_type__one_to_many__nested():
    task = TaskFactory.create(
        name="Task",
        steps__name="Step",
    )

    data = {
        "steps": ["foo"],
    }

    handler = MutationHandler[Task](model=Task)

    msg = "Invalid input data for field 'steps': ['foo']"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.update(task, data)


def test_mutation_handler__invalid_type__many_to_many():
    task = TaskFactory.create(
        name="Task",
        assignees__name="Assignee",
    )

    data = {
        "assignees": "foo",
    }

    handler = MutationHandler[Task](model=Task)

    msg = "Invalid input data for field 'assignees': 'foo'"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.update(task, data)


def test_mutation_handler__invalid_type__many_to_many__reverse():
    task = TaskFactory.create(
        name="Task",
        reports__name="Report",
    )

    data = {
        "reports": "foo",
    }

    handler = MutationHandler[Task](model=Task)

    msg = "Invalid input data for field 'reports': 'foo'"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.update(task, data)


def test_mutation_handler__invalid_type__many_to_many__item():
    task = TaskFactory.create(
        name="Task",
        assignees__name="Assignee",
    )

    data = {
        "assignees": ["foo"],
    }

    handler = MutationHandler[Task](model=Task)

    msg = "Invalid input data for field 'assignees': ['foo']"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.update(task, data)


def test_mutation_handler__invalid_data__forward_one_to_one():
    task = TaskFactory.create()

    data = {
        "request": "foo",
    }

    handler = MutationHandler[Task](model=Task)

    msg = "Invalid input data for field 'request': 'foo'"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.update(task, data)


def test_mutation_handler__invalid_data__forward_many_to_one():
    task = TaskFactory.create()

    data = {
        "project": "foo",
    }

    handler = MutationHandler[Task](model=Task)

    msg = "Invalid input data for field 'project': 'foo'"
    with pytest.raises(GraphQLInvalidInputDataError, match=exact(msg)):
        handler.update(task, data)
