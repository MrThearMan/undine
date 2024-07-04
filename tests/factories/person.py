from factory import faker

from example_project.app.models import Person

from ._base import GenericDjangoModelFactory, OneToManyFactory


class PersonFactory(GenericDjangoModelFactory[Person]):
    class Meta:
        model = Person

    name = faker.Faker("name")
    email = faker.Faker("email")

    comments = OneToManyFactory("tests.factories.comment.CommentFactory")
    teams = OneToManyFactory("tests.factories.team.TeamFactory")
    tasks = OneToManyFactory("tests.factories.task.TaskFactory")
