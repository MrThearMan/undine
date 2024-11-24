import pytest

from example_project.app.models import Task, TaskTypeChoices
from tests.factories import ProjectFactory, ServiceRequestFactory, TaskFactory
from undine.utils.bulk_mutation_handler import BulkMutationHandler

pytestmark = [
    pytest.mark.django_db,
]


def test_bulk_mutation_handler__create():
    request = ServiceRequestFactory.create(details="Test request")
    project = ProjectFactory.create(name="Test project")

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.TASK.value,
            "request": request.pk,
            "project": project.pk,
        },
    ]

    handler = BulkMutationHandler[Task](model=Task)
    instances = handler.create_many(data)

    assert len(instances) == 1
    assert instances[0].pk is not None
    assert instances[0].name == "Test task"
    assert instances[0].type == TaskTypeChoices.TASK
    assert instances[0].request == request
    assert instances[0].project == project


def test_bulk_mutation_handler__update():
    request = ServiceRequestFactory.create(details="Test request")
    project = ProjectFactory.create(name="Test project")
    task = TaskFactory.create(name="Task", type=TaskTypeChoices.BUG_FIX.value)

    data = [
        {
            "pk": task.pk,
            "name": "Test task",
            "type": TaskTypeChoices.TASK.value,
            "request": request.pk,
            "project": project.pk,
        },
    ]

    handler = BulkMutationHandler[Task](model=Task)
    instances = handler.update_many(data, lookup_field="pk")

    assert len(instances) == 1
    assert instances[0].pk is not None
    assert instances[0].name == "Test task"
    assert instances[0].type == TaskTypeChoices.TASK
    assert instances[0].request == request
    assert instances[0].project == project


# TODO: more tests
