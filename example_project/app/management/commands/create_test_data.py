from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand

from tests.factories import (
    AcceptanceCriteriaFactory,
    CommentFactory,
    PersonFactory,
    ProjectFactory,
    ReportFactory,
    ServiceRequestFactory,
    TaskFactory,
    TaskResultFactory,
    TaskStepFactory,
    TeamFactory,
)


class Command(BaseCommand):
    help = "Create test data."

    def handle(self, *args: Any, **options: Any) -> None:
        create_test_data()


def create_test_data() -> None:  # noqa: PLR0914
    call_command("flush", "--noinput")

    print("Creating users...")
    User.objects.create_superuser("admin", "admin@example.com", "admin")

    print("Creating persons...")
    person_1 = PersonFactory.create()
    person_2 = PersonFactory.create()
    person_3 = PersonFactory.create()
    person_4 = PersonFactory.create()
    person_5 = PersonFactory.create()

    print("Creating service requests...")
    service_request_1 = ServiceRequestFactory.create()
    service_request_2 = ServiceRequestFactory.create()

    print("Creating teams...")
    team_1 = TeamFactory.create()
    team_2 = TeamFactory.create()

    team_1.members.add(person_1, person_2)
    team_2.members.add(person_2, person_3, person_4)

    print("Creating projects...")
    project_1 = ProjectFactory.create(team=team_1)
    project_2 = ProjectFactory.create(team=team_2)
    project_3 = ProjectFactory.create(team=team_1)

    print("Creating tasks...")
    task_1 = TaskFactory.create(request=service_request_1, project=project_1)
    task_2 = TaskFactory.create(project=project_2)
    task_3 = TaskFactory.create(request=service_request_2, project=project_3)
    task_4 = TaskFactory.create(project=project_1)

    task_1.assignees.add(person_1, person_4)
    task_2.assignees.add(person_3)
    task_3.assignees.add(person_2, person_5)
    task_4.assignees.add(person_1, person_2, person_5)

    print("Creating task results...")
    TaskResultFactory.create(task=task_1)
    TaskResultFactory.create(task=task_4)

    print("Creating task steps...")
    TaskStepFactory.create(done=True, task=task_1)
    TaskStepFactory.create(done=False, task=task_1)
    TaskStepFactory.create(done=False, task=task_1)
    TaskStepFactory.create(done=False, task=task_2)
    TaskStepFactory.create(done=True, task=task_3)
    TaskStepFactory.create(done=False, task=task_3)
    TaskStepFactory.create(done=True, task=task_4)
    TaskStepFactory.create(done=True, task=task_4)
    TaskStepFactory.create(done=False, task=task_4)

    print("Creating acceptance criteria...")
    AcceptanceCriteriaFactory.create(fulfilled=True, task=task_1)
    AcceptanceCriteriaFactory.create(fulfilled=False, task=task_1)
    AcceptanceCriteriaFactory.create(fulfilled=False, task=task_2)
    AcceptanceCriteriaFactory.create(fulfilled=False, task=task_3)
    AcceptanceCriteriaFactory.create(fulfilled=False, task=task_4)
    AcceptanceCriteriaFactory.create(fulfilled=False, task=task_4)
    AcceptanceCriteriaFactory.create(fulfilled=False, task=task_4)
    AcceptanceCriteriaFactory.create(fulfilled=True, task=task_4)

    print("Creating reports...")
    report_1 = ReportFactory.create()
    report_2 = ReportFactory.create()
    report_3 = ReportFactory.create()
    report_4 = ReportFactory.create()

    report_1.tasks.add(task_1, task_2, task_3)
    report_2.tasks.add(task_4)
    report_3.tasks.add(task_2, task_4)
    report_4.tasks.add(task_1)

    print("Creating comments...")
    CommentFactory.create(commenter=person_1, target=task_1)
    CommentFactory.create(commenter=person_2, target=task_1)
    CommentFactory.create(commenter=person_2, target=task_2)
    CommentFactory.create(commenter=person_2, target=task_3)
    CommentFactory.create(commenter=person_2, target=project_1)
    CommentFactory.create(commenter=person_2, target=project_2)
    CommentFactory.create(commenter=person_3, target=task_2)
    CommentFactory.create(commenter=person_3, target=task_4)
    CommentFactory.create(commenter=person_5, target=task_1)
    CommentFactory.create(commenter=person_5, target=task_4)
    CommentFactory.create(commenter=person_5, target=project_3)

    print("Done!")
