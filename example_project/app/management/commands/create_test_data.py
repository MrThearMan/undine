from typing import Any

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from faker import Faker

from example_project.app.models import (
    AcceptanceCriteria,
    Comment,
    Person,
    Project,
    Report,
    ServiceRequest,
    Task,
    TaskResult,
    TaskStep,
    TaskTypeChoices,
    Team,
)

faker = Faker(locale="en_US")


class Command(BaseCommand):
    help = "Create test data."

    def handle(self, *args: Any, **options: Any) -> None:
        create_test_data()


def create_test_data() -> None:
    call_command("flush", "--noinput")

    print("Creating users...")
    User.objects.create_superuser("admin", "admin@example.com", "admin")

    print("Creating persons...")
    person_1 = Person.objects.create(name=faker.name(), email=faker.email())
    person_2 = Person.objects.create(name=faker.name(), email=faker.email())
    person_3 = Person.objects.create(name=faker.name(), email=faker.email())
    person_4 = Person.objects.create(name=faker.name(), email=faker.email())
    person_5 = Person.objects.create(name=faker.name(), email=faker.email())

    print("Creating service requests...")
    service_request_1 = ServiceRequest.objects.create(details=faker.text())
    service_request_2 = ServiceRequest.objects.create(details=faker.text())

    print("Creating teams...")
    team_1 = Team.objects.create(name=faker.name())
    team_1.members.add(person_1, person_2)
    team_2 = Team.objects.create(name=faker.name())
    team_2.members.add(person_2, person_3, person_4)

    print("Creating projects...")
    project_1 = Project.objects.create(name=faker.name(), team=team_1)
    project_2 = Project.objects.create(name=faker.name(), team=team_2)
    project_3 = Project.objects.create(name=faker.name(), team=team_1)

    print("Creating tasks...")
    task_1 = Task.objects.create(
        name=faker.name(), type=TaskTypeChoices.STORY, request=service_request_1, project=project_1
    )
    task_1.assignees.add(person_1, person_4)

    task_2 = Task.objects.create(name=faker.name(), type=TaskTypeChoices.BUG_FIX, project=project_2)
    task_2.assignees.add(person_3)

    task_3 = Task.objects.create(
        name=faker.name(), type=TaskTypeChoices.TASK, request=service_request_2, project=project_3
    )
    task_3.assignees.add(person_2, person_5)

    task_4 = Task.objects.create(name=faker.name(), type=TaskTypeChoices.STORY, project=project_1)
    task_4.assignees.add(person_1, person_2, person_5)

    print("Creating task results...")
    TaskResult.objects.create(details=faker.text(), time_used=faker.time_delta(), task=task_1)
    TaskResult.objects.create(details=faker.text(), time_used=faker.time_delta(), task=task_4)

    print("Creating task steps...")
    TaskStep.objects.create(name=faker.name(), done=True, task=task_1)
    TaskStep.objects.create(name=faker.name(), done=False, task=task_1)
    TaskStep.objects.create(name=faker.name(), done=False, task=task_1)
    TaskStep.objects.create(name=faker.name(), done=False, task=task_2)
    TaskStep.objects.create(name=faker.name(), done=True, task=task_3)
    TaskStep.objects.create(name=faker.name(), done=False, task=task_3)
    TaskStep.objects.create(name=faker.name(), done=True, task=task_4)
    TaskStep.objects.create(name=faker.name(), done=True, task=task_4)
    TaskStep.objects.create(name=faker.name(), done=False, task=task_4)

    print("Creating acceptance criteria...")
    AcceptanceCriteria.objects.create(details=faker.text(), fulfilled=True, task=task_1)
    AcceptanceCriteria.objects.create(details=faker.text(), fulfilled=False, task=task_1)
    AcceptanceCriteria.objects.create(details=faker.text(), fulfilled=False, task=task_2)
    AcceptanceCriteria.objects.create(details=faker.text(), fulfilled=False, task=task_3)
    AcceptanceCriteria.objects.create(details=faker.text(), fulfilled=False, task=task_4)
    AcceptanceCriteria.objects.create(details=faker.text(), fulfilled=False, task=task_4)
    AcceptanceCriteria.objects.create(details=faker.text(), fulfilled=False, task=task_4)
    AcceptanceCriteria.objects.create(details=faker.text(), fulfilled=True, task=task_4)

    print("Creating reports...")
    report_1 = Report.objects.create(name=faker.name(), content=faker.text())
    report_1.tasks.add(task_1, task_2, task_3)

    report_2 = Report.objects.create(name=faker.name(), content=faker.text())
    report_2.tasks.add(task_4)

    report_3 = Report.objects.create(name=faker.name(), content=faker.text())
    report_3.tasks.add(task_2, task_4)

    report_4 = Report.objects.create(name=faker.name(), content=faker.text())
    report_4.tasks.add(task_1)

    print("Creating comments...")
    Comment.objects.create(contents=faker.text(), commenter=person_1, target=task_1)
    Comment.objects.create(contents=faker.text(), commenter=person_2, target=task_1)
    Comment.objects.create(contents=faker.text(), commenter=person_2, target=task_2)
    Comment.objects.create(contents=faker.text(), commenter=person_2, target=task_3)
    Comment.objects.create(contents=faker.text(), commenter=person_2, target=project_1)
    Comment.objects.create(contents=faker.text(), commenter=person_2, target=project_2)
    Comment.objects.create(contents=faker.text(), commenter=person_3, target=task_2)
    Comment.objects.create(contents=faker.text(), commenter=person_3, target=task_4)
    Comment.objects.create(contents=faker.text(), commenter=person_5, target=task_1)
    Comment.objects.create(contents=faker.text(), commenter=person_5, target=task_4)
    Comment.objects.create(contents=faker.text(), commenter=person_5, target=project_3)

    print("Done!")
