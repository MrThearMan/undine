from factory import faker

from example_project.app.models import Team

from ._base import GenericDjangoModelFactory, ManyToManyFactory


class TeamFactory(GenericDjangoModelFactory[Team]):
    class Meta:
        model = Team

    name = faker.Faker("name")

    members = ManyToManyFactory("tests.factories.task.PersonFactory")
