from factory import faker

from example_project.app.models import Person

from ._base import GenericDjangoModelFactory, ManyToManyFactory, OneToManyFactory


class PersonFactory(GenericDjangoModelFactory[Person]):
    class Meta:
        model = Person

    name = faker.Faker("name")
    email = faker.Faker("email")

    comments = OneToManyFactory("tests.factories.comment.CommentFactory")
    teams = ManyToManyFactory("tests.factories.team.TeamFactory")
    tasks = ManyToManyFactory("tests.factories.task.TaskFactory")
