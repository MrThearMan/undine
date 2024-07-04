from factory import SubFactory, faker

from example_project.app.models import Project

from ._base import GenericDjangoModelFactory, OneToManyFactory


class ProjectFactory(GenericDjangoModelFactory[Project]):
    class Meta:
        model = Project

    name = faker.Faker("name")
    email = faker.Faker("email")

    team = SubFactory("tests.factories.task.TaskFactory")
    tasks = OneToManyFactory("tests.factories.task.TaskFactory")
