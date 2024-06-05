from factory import fuzzy

from example_project.app.models import AcceptanceCriteria

from ._base import ForeignKeyFactory, GenericDjangoModelFactory


class AcceptanceCriteriaFactory(GenericDjangoModelFactory[AcceptanceCriteria]):
    class Meta:
        model = AcceptanceCriteria

    details = fuzzy.FuzzyText(length=100)
    fulfilled = fuzzy.FuzzyChoice([True, False])

    task = ForeignKeyFactory("tests.factories.TaskFactory")
