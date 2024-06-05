from factory import fuzzy

from example_project.app.models import TaskStep

from ._base import ForeignKeyFactory, GenericDjangoModelFactory, UndineFaker


class TaskStepFactory(GenericDjangoModelFactory[TaskStep]):
    class Meta:
        model = TaskStep

    name = UndineFaker("name")
    done = fuzzy.FuzzyChoice([True, False])

    task = ForeignKeyFactory("tests.factories.TaskFactory")
