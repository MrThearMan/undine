from factory import SubFactory, faker, fuzzy

from example_project.app.models import TaskStep

from ._base import GenericDjangoModelFactory


class TaskStepFactory(GenericDjangoModelFactory[TaskStep]):
    class Meta:
        model = TaskStep

    name = faker.Faker("name")
    done = fuzzy.FuzzyChoice([True, False])

    task = SubFactory("tests.factories.task.TaskFactory")
