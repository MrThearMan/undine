from example_project.app.models import Team

from ._base import GenericDjangoModelFactory, ManyToManyFactory, ReverseForeignKeyFactory, UndineFaker


class TeamFactory(GenericDjangoModelFactory[Team]):
    class Meta:
        model = Team

    name = UndineFaker("name")

    members = ManyToManyFactory("tests.factories.PersonFactory")
    projects = ReverseForeignKeyFactory("tests.factories.ProjectFactory")
