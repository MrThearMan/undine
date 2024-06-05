from factory import SubFactory, fuzzy

from example_project.app.models import AcceptanceCriteria

from ._base import GenericDjangoModelFactory


class AcceptanceCriteriaFactory(GenericDjangoModelFactory[AcceptanceCriteria]):
    class Meta:
        model = AcceptanceCriteria

    details = fuzzy.FuzzyText(length=100)
    fulfilled = fuzzy.FuzzyChoice([True, False])

    task = SubFactory("tests.factories.task.TaskFactory")
