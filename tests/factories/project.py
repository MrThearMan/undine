from factory import SubFactory

from example_project.app.models import Project

from ._base import GenericDjangoModelFactory, ReverseForeignKeyFactory, UndineFaker


class ProjectFactory(GenericDjangoModelFactory[Project]):
    class Meta:
        model = Project

    name = UndineFaker("name")

    team = SubFactory("tests.factories.TeamFactory")
    tasks = ReverseForeignKeyFactory("tests.factories.TaskFactory")
