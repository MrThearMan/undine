from __future__ import annotations

import datetime as dt

import factory
from factory import fuzzy

from example_project.app.models import TaskResult

from ._base import ForwardOneToOneFactory, GenericDjangoModelFactory


class TaskResultFactory(GenericDjangoModelFactory[TaskResult]):
    class Meta:
        model = TaskResult

    details = fuzzy.FuzzyText(length=100)
    time_used = dt.timedelta(hours=10)
    created_at = factory.LazyFunction(dt.datetime.now)

    task = ForwardOneToOneFactory("tests.factories.TaskFactory")
