from factory import fuzzy

from example_project.app.models import TaskObjective

from ._base import GenericDjangoModelFactory, NullableSubFactory


class TaskObjectiveFactory(GenericDjangoModelFactory[TaskObjective]):
    class Meta:
        model = TaskObjective

    details = fuzzy.FuzzyText(length=100)

    task = NullableSubFactory("tests.factories.task.TaskFactory", null=True)
