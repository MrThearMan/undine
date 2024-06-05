from factory import faker, fuzzy

from example_project.app.models import Report

from ._base import GenericDjangoModelFactory, ManyToManyFactory


class ReportFactory(GenericDjangoModelFactory[Report]):
    class Meta:
        model = Report

    name = faker.Faker("name")
    content = fuzzy.FuzzyText(length=100)

    tasks = ManyToManyFactory("tests.factories.task.TaskFactory")
