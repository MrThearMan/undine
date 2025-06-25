from __future__ import annotations

import pytest
from django.db.models import Value

from example_project.app.models import Comment, Person, Project, Task
from tests.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory
from undine import (
    Calculation,
    CalculationArgument,
    DjangoExpression,
    Entrypoint,
    Field,
    GQLInfo,
    QueryType,
    RootType,
    create_schema,
)


@pytest.mark.django_db
def test_optimizer__aliases__entrypoint(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
         myTasks: tasks {
            pk
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "myTasks": [
            {
                "pk": task_1.pk,
                "name": "foo",
            },
            {
                "pk": task_2.pk,
                "name": "bar",
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__model_field(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
          tasks {
            pk
            title: name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "title": "foo",
            },
            {
                "pk": task_2.pk,
                "title": "bar",
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__model_field__multiple(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
          tasks {
            pk
            foo: name
            bar: name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "foo": "foo",
                "bar": "foo",
            },
            {
                "pk": task_2.pk,
                "foo": "bar",
                "bar": "bar",
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__to_one(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project_1 = ProjectFactory.create(name="foo")
    project_2 = ProjectFactory.create(name="bar")

    task_1 = TaskFactory.create(name="foo", project=project_1)
    task_2 = TaskFactory.create(name="bar", project=project_2)

    query = """
        query {
          tasks {
            pk
            name
            in: project {
              pk
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "name": "foo",
                "in": {
                    "pk": project_1.pk,
                    "name": "foo",
                },
            },
            {
                "pk": task_2.pk,
                "name": "bar",
                "in": {
                    "pk": project_2.pk,
                    "name": "bar",
                },
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__to_one__multiple(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project_1 = ProjectFactory.create(name="foo")
    project_2 = ProjectFactory.create(name="bar")

    task_1 = TaskFactory.create(name="foo", project=project_1)
    task_2 = TaskFactory.create(name="bar", project=project_2)

    query = """
        query {
          tasks {
            pk
            name
            foo: project {
              pk
            }
            bar: project {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "name": "foo",
                "foo": {
                    "pk": project_1.pk,
                },
                "bar": {
                    "name": "foo",
                },
            },
            {
                "pk": task_2.pk,
                "name": "bar",
                "foo": {
                    "pk": project_2.pk,
                },
                "bar": {
                    "name": "bar",
                },
            },
        ],
    }

    # Don't make separate prefetches for the aliased to-one relations.
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__to_many(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    person_1 = PersonFactory.create(name="foo", tasks=[task_1])
    person_2 = PersonFactory.create(name="bar", tasks=[task_1])
    person_3 = PersonFactory.create(name="baz", tasks=[task_2])
    person_4 = PersonFactory.create(name="bax", tasks=[task_2])

    query = """
        query {
          tasks {
            pk
            name
            by: assignees {
              pk
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "name": "foo",
                "by": [
                    {"pk": person_1.pk, "name": "foo"},
                    {"pk": person_2.pk, "name": "bar"},
                ],
            },
            {
                "pk": task_2.pk,
                "name": "bar",
                "by": [
                    {"pk": person_3.pk, "name": "baz"},
                    {"pk": person_4.pk, "name": "bax"},
                ],
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__to_many__multiple(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    person_1 = PersonFactory.create(name="foo", tasks=[task_1])
    person_2 = PersonFactory.create(name="bar", tasks=[task_1])
    person_3 = PersonFactory.create(name="baz", tasks=[task_2])
    person_4 = PersonFactory.create(name="bax", tasks=[task_2])

    query = """
        query {
          tasks {
            pk
            name
            foo: assignees {
              pk
            }
            bar: assignees {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "name": "foo",
                "foo": [
                    {"pk": person_1.pk},
                    {"pk": person_2.pk},
                ],
                "bar": [
                    {"name": "foo"},
                    {"name": "bar"},
                ],
            },
            {
                "pk": task_2.pk,
                "name": "bar",
                "foo": [
                    {"pk": person_3.pk},
                    {"pk": person_4.pk},
                ],
                "bar": [
                    {"name": "baz"},
                    {"name": "bax"},
                ],
            },
        ],
    }

    # Need to make separate prefetches for the aliased to-many relations,
    # since they might have different filtering/ordering applied.
    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__generic_foreign_key(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        pk = Field()
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task")
    project = ProjectFactory.create(name="Project")
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=project)

    query = """
        query {
          comments {
            to: target {
              ... on ProjectType {
                name
              }
              ... on TaskType {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "comments": [
            {
                "to": {"name": "Task"},
            },
            {
                "to": {"name": "Project"},
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__generic_foreign_key__multiple(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        pk = Field()
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task")
    project = ProjectFactory.create(name="Project")
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=project)

    query = """
        query {
          comments {
            foo: target {
              ... on ProjectType {
                pk
              }
              ... on TaskType {
                pk
              }
            }
            bar: target {
              ... on ProjectType {
                name
              }
              ... on TaskType {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "comments": [
            {
                "foo": {"pk": 1},
                "bar": {"name": "Task"},
            },
            {
                "foo": {"pk": 1},
                "bar": {"name": "Project"},
            },
        ]
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__aliases__calculated(graphql, undine_settings) -> None:
    class ExampleCalculation(Calculation[int | None]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        calc = Field(ExampleCalculation)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
          tasks {
            pk
            calculation: calc(value: 1)
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "calculation": 1,
            },
            {
                "pk": task_2.pk,
                "calculation": 1,
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__calculated__multiple(graphql, undine_settings) -> None:
    class ExampleCalculation(Calculation[int | None]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        calc = Field(ExampleCalculation)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
          tasks {
            pk
            foo: calc(value: 1)
            bar: calc(value: 2)
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "foo": 1,
                "bar": 2,
            },
            {
                "pk": task_2.pk,
                "foo": 1,
                "bar": 2,
            },
        ],
    }

    response.assert_query_count(1)
