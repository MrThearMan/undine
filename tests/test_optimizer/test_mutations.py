import pytest
from django.contrib.contenttypes.models import ContentType

from example_project.app.models import Comment, Report, ServiceRequest, Task, TaskStep, TaskTypeChoices
from tests.factories import PersonFactory, ServiceRequestFactory, TaskFactory
from undine import Entrypoint, Field, Input, MutationType, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_mutation_output__create__one_to_one(graphql, undine_settings):
    class ServiceRequestType(QueryType, model=ServiceRequest, auto=False):
        pk = Field()
        details = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        request = Field(ServiceRequestType)

    class ServiceRequestMutation(MutationType, model=ServiceRequest, mutation_kind="nested"): ...

    class TaskCreateMutation(MutationType, model=Task, auto=False):
        name = Input()
        type = Input()
        request = Input(ServiceRequestMutation)

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
            request {
              details
            }
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": {"details": "Test request"},
    }

    response = graphql.query(query, variables={"input": data})

    assert response.data == {
        "createTask": {
            "name": "Test task",
            "request": {
                "details": "Test request",
            },
        },
    }

    # 1 query for creating the service request
    # ...
    # 1 query for checking if the task service request exists
    # 1 query for checking if the task project exists
    # ...
    # 1 query for creating the task
    # ...
    # 1 query for fetching tasks and requests after the creation
    response.assert_query_count(5)


@pytest.mark.django_db
def test_mutation_output__create__one_to_many(graphql, undine_settings):
    class TaskStepType(QueryType, model=TaskStep, auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        steps = Field(TaskStepType)

    class TaskStepMutation(MutationType, model=TaskStep, mutation_kind="nested"): ...

    class TaskCreateMutation(MutationType, model=Task, auto=False):
        name = Input()
        type = Input()
        steps = Input(TaskStepMutation)

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
            steps {
              name
            }
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "steps": [{"name": "Test step"}],
    }

    response = graphql(query, variables={"input": data})

    assert response.data == {
        "createTask": {
            "name": "Test task",
            "steps": [
                {
                    "name": "Test step",
                },
            ],
        },
    }

    # 1 query for creating the task
    # 1 query for checking if the task exists
    # ...
    # 1 query for creating the task steps
    # 1 query for removing unupdated steps
    # ...
    # 1 query for fetching tasks and requests after the creation
    # 1 query for fetching task steps after the creation
    response.assert_query_count(6)


@pytest.mark.django_db
def test_mutation_output__create__many_to_many(graphql, undine_settings):
    class ReportType(QueryType, model=Report, auto=False):
        pk = Field()
        name = Field()
        content = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        reports = Field(ReportType)

    class ReportMutation(MutationType, model=Report, mutation_kind="nested"): ...

    class TaskCreateMutation(MutationType, model=Task, auto=False):
        name = Input()
        type = Input()
        reports = Input(ReportMutation)

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
            reports {
              name
            }
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "reports": [{"name": "Test report", "content": "Test report content"}],
    }

    response = graphql(query, variables={"input": data})

    assert response.data == {
        "createTask": {
            "name": "Test task",
            "reports": [
                {
                    "name": "Test report",
                },
            ],
        },
    }

    # 1 query for creating the task
    # 1 query for creating the task reports
    # 2 queries for creating linking tasks to reports
    # ...
    # 1 query for fetching tasks and requests after the creation
    # 1 query for fetching task reports after the creation
    response.assert_query_count(6)


@pytest.mark.django_db
def test_mutation_output__create__generic_relations(graphql, undine_settings):
    class CommentType(QueryType, model=Comment, auto=False):
        pk = Field()
        contents = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        comments = Field(CommentType)

    class CommentMutation(MutationType, model=Comment, mutation_kind="nested"): ...

    class TaskCreateMutation(MutationType, model=Task, auto=False):
        name = Input()
        type = Input()
        comments = Input(CommentMutation)

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    person = PersonFactory.create()

    # Cache the content type for the Task model.
    ContentType.objects.get_for_model(Task)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
            comments {
              contents
            }
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "comments": [{"contents": "Test comment", "commenter": person.pk}],
    }

    response = graphql(query, variables={"input": data})

    assert response.data == {
        "createTask": {
            "name": "Test task",
            "comments": [
                {
                    "contents": "Test comment",
                },
            ],
        },
    }

    # 1 query for creating the task
    # ...
    # 1 query for fetching the person for the comment
    # 1 query for checking if the person exists
    # 1 query for checking if the comment's content type exists
    # ...
    # 1 query for creating the comments
    # 1 query for removing unupdated comments
    # ...
    # 1 query for fetching tasks and requests after the creation
    # 1 query for fetching task comments after the creation
    response.assert_query_count(8)


@pytest.mark.django_db
def test_mutation_output__update__one_to_one(graphql, undine_settings):
    class ServiceRequestType(QueryType, model=ServiceRequest, auto=False):
        pk = Field()
        details = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        request = Field(ServiceRequestType)

    class TaskUpdateMutation(MutationType, model=Task): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", request__details="Test request")

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            request {
              details
            }
          }
        }
    """

    data = {"pk": task.pk, "name": "Updated task"}

    response = graphql(query, variables={"input": data})

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "request": {
                "details": "Test request",
            },
        },
    }

    # 1 query for fetching the task for updating
    # 1 query for checking if task service request exists
    # 1 query for checking if task project exists
    # 1 query for checking that task exists for updating
    # ...
    # 1 query for updating the task
    # ...
    # 1 query for fetching tasks and requests after the update
    response.assert_query_count(6)


@pytest.mark.django_db
def test_mutation_output__update__one_to_many(graphql, undine_settings):
    class TaskStepType(QueryType, model=TaskStep, auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        steps = Field(TaskStepType)

    class TaskUpdateMutation(MutationType, model=Task): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", steps__name="Test step")

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            steps {
              name
            }
          }
        }
    """

    data = {"pk": task.pk, "name": "Updated task"}

    response = graphql(query, variables={"input": data})

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "steps": [
                {
                    "name": "Test step",
                },
            ],
        },
    }

    # 1 query for fetching the task for updating
    # 1 query for checking if task service request exists
    # 1 query for checking if task project exists
    # 1 query for checking that task exists for updating
    # ...
    # 1 query for updating the task
    # ...
    # 1 query for fetching tasks after the update
    # 1 query for fetching task steps after the update
    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_output__update__many_to_many(graphql, undine_settings):
    class ReportType(QueryType, model=Report, auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        reports = Field(ReportType)

    class TaskUpdateMutation(MutationType, model=Task): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", reports__name="Test report")

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            reports {
              name
            }
          }
        }
    """

    data = {"pk": task.pk, "name": "Updated task"}

    response = graphql(query, variables={"input": data})

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "reports": [
                {
                    "name": "Test report",
                },
            ],
        },
    }

    # 1 query for fetching the task for updating
    # 1 query for checking if task service request exists
    # 1 query for checking if task project exists
    # 1 query for checking that task exists for updating
    # ...
    # 1 query for updating the task
    # ...
    # 1 query for fetching tasks after the update
    # 1 query for fetching task reports after the update
    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_output__bulk_create__one_to_one(graphql, undine_settings):
    class ServiceRequestType(QueryType, model=ServiceRequest, auto=False):
        pk = Field()
        details = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        request = Field(ServiceRequestType)

    class TaskCreateMutation(MutationType, model=Task, auto=False):
        name = Input()
        type = Input()
        request = Input()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    service_request = ServiceRequestFactory.create(details="Test request")

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTasks(input: $input) {
            name
            request {
              details
            }
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": service_request.pk,
        },
    ]

    response = graphql.query(query, variables={"input": data})

    assert response.data == {
        "bulkCreateTasks": [
            {
                "name": "Test task",
                "request": {
                    "details": "Test request",
                },
            },
        ],
    }

    # 1 query for fetching service requests for the tasks
    # ...
    # 1 query for checking if task service request exists
    # 1 query for checking if task project exists
    # ...
    # 1 query for creating the task
    # ...
    # 1 query for fetching tasks and requests after the creation
    response.assert_query_count(5)


@pytest.mark.django_db
def test_mutation_output__bulk_update__one_to_one(graphql, undine_settings):
    class ServiceRequestType(QueryType, model=ServiceRequest, auto=False):
        pk = Field()
        details = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        request = Field(ServiceRequestType)

    class TaskUpdateMutation(MutationType, model=Task, auto=False):
        name = Input()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", request__details="Test request")

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            request {
              details
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
        },
    ]

    response = graphql.query(query, variables={"input": data})

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "request": {
                    "details": "Test request",
                },
            },
        ],
    }

    # 1 query for fetching all tasks for updating
    # ...
    # 1 query for checking if task service request exists
    # 1 query for checking if task project exists
    # 1 query for checking if task exists
    # ...
    # 1 query for updating the tasks
    # ...
    # 1 query for fetching tasks and requests after the creation
    response.assert_query_count(6)


@pytest.mark.django_db
def test_mutation_output__bulk_update__one_to_many(graphql, undine_settings):
    class TaskStepType(QueryType, model=TaskStep, auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        steps = Field(TaskStepType)

    class TaskUpdateMutation(MutationType, model=Task, auto=False):
        name = Input()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", steps__name="Test step")

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            steps {
              name
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
        },
    ]

    response = graphql.query(query, variables={"input": data})

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "steps": [
                    {
                        "name": "Test step",
                    },
                ],
            },
        ],
    }

    # 1 query for fetching all tasks for updating
    # ...
    # 1 query for checking if task service request exists
    # 1 query for checking if task project exists
    # 1 query for checking if task exists
    # ...
    # 1 query for updating the tasks
    # ...
    # 1 query for fetching tasks after the creation
    # 1 query for fetching task steps after the creation
    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_output__bulk_update__many_to_many(graphql, undine_settings):
    class ReportType(QueryType, model=Report, auto=False):
        pk = Field()
        name = Field()

    class TaskType(QueryType, model=Task, auto=False):
        pk = Field()
        name = Field()
        reports = Field(ReportType)

    class TaskUpdateMutation(MutationType, model=Task, auto=False):
        name = Input()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", reports__name="Test report")

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            reports {
              name
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
        },
    ]

    response = graphql.query(query, variables={"input": data})

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "reports": [
                    {
                        "name": "Test report",
                    },
                ],
            },
        ],
    }

    # 1 query for fetching all tasks for updating
    # ...
    # 1 query for checking if the task service request exists
    # 1 query for checking if the task project exists
    # 1 query for checking if the task exists
    # ...
    # 1 query for updating the tasks
    # ...
    # 1 query for fetching tasks after the creation
    # 1 query for fetching task reports after the creation
    response.assert_query_count(7)


# TODO: Generic relations. Use "ContentType.objects.get_for_model(Task)" to cache the content type.
# TODO: Add multiple entities to bulk mutations.
