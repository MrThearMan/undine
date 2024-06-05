from example_project.app.models import Person

from ._base import GenericDjangoModelFactory, ManyToManyFactory, ReverseForeignKeyFactory, UndineFaker


class PersonFactory(GenericDjangoModelFactory[Person]):
    class Meta:
        model = Person

    name = UndineFaker("name")
    email = UndineFaker("email", unique=True)

    comments = ReverseForeignKeyFactory("tests.factories.CommentFactory")
    teams = ManyToManyFactory("tests.factories.TeamFactory")
    tasks = ManyToManyFactory("tests.factories.TaskFactory")
