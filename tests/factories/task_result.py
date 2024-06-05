import datetime

import factory
from factory import SubFactory, fuzzy

from example_project.app.models import TaskResult

from ._base import GenericDjangoModelFactory


class TaskResultFactory(GenericDjangoModelFactory[TaskResult]):
    class Meta:
        model = TaskResult

    details = fuzzy.FuzzyText(length=100)
    time_used = datetime.timedelta(hours=10)
    created_at = factory.LazyFunction(datetime.datetime.now)

    task = SubFactory("tests.factories.task.TaskFactory")
