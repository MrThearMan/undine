from factory import fuzzy

from example_project.app.models import TaskObjective

from ._base import ForwardOneToOneFactory, GenericDjangoModelFactory


class TaskObjectiveFactory(GenericDjangoModelFactory[TaskObjective]):
    class Meta:
        model = TaskObjective

    details = fuzzy.FuzzyText(length=100)

    task = ForwardOneToOneFactory("tests.factories.TaskFactory")
