import datetime

import factory
from factory import SubFactory, faker, fuzzy

from example_project.app.models import Task, TaskTypeChoices

from ._base import GenericDjangoModelFactory, ManyToManyFactory, NullableSubFactory, OneToManyFactory, ReverseSubFactory


class TaskFactory(GenericDjangoModelFactory[Task]):
    class Meta:
        model = Task

    name = faker.Faker("name")
    type = fuzzy.FuzzyChoice(TaskTypeChoices.values)
    created_at = factory.LazyFunction(datetime.datetime.now)

    related_tasks = ManyToManyFactory("tests.factories.task.TaskFactory")

    request = NullableSubFactory("tests.factories.service_request.ServiceRequestFactory")
    project = SubFactory("tests.factories.project.ProjectFactory")
    assignees = ManyToManyFactory("tests.factories.person.PersonFactory")

    result = ReverseSubFactory("tests.factories.task_result.TaskResultFactory")
    objective = ReverseSubFactory("tests.factories.task_objective.TaskObjectiveFactory")
    steps = OneToManyFactory("tests.factories.task_step.TaskStepFactory")
    acceptance_criteria = OneToManyFactory("tests.factories.acceptance_criteria.AcceptanceCriteriaFactory")
    reports = ManyToManyFactory("tests.factories.report.ReportFactory")

    comments = OneToManyFactory("tests.factories.comment.CommentFactory")
