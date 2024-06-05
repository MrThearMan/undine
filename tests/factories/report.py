from factory import fuzzy

from example_project.app.models import Report

from ._base import GenericDjangoModelFactory, ManyToManyFactory, UndineFaker


class ReportFactory(GenericDjangoModelFactory[Report]):
    class Meta:
        model = Report

    name = UndineFaker("name")
    content = fuzzy.FuzzyText(length=100)

    tasks = ManyToManyFactory("tests.factories.TaskFactory")
