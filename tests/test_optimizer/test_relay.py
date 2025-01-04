import pytest

from example_project.app.models import Comment, Person, Project, Report, Task, TaskStep, Team
from tests.factories import CommentFactory, PersonFactory, ReportFactory, TaskFactory, TaskStepFactory, TeamFactory
from undine import Entrypoint, Field, QueryType, RootOperationType, create_schema
from undine.relay import Connection, Node, offset_to_cursor, to_global_id

# Relay Node interface


@pytest.mark.django_db
def test_optimizer__relay__node(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        node = Entrypoint(Node)
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task")

    global_id = to_global_id(typename=TaskType.__typename__, object_id=task.pk)

    query = """
        query NodeQuery($global_id: ID!) {
          node(id: $global_id) {
            __typename
            ... on TaskType {
              name
            }
          }
        }
    """

    response = graphql(query, variables={"global_id": global_id})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "node": {
            "__typename": "TaskType",
            "name": "Task",
        },
    }

    # 1 query for fetching the task
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__node__joins(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False):
        name = Field()

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        project = Field(ProjectType)
        assignees = Field(PersonType)

    class Query(RootOperationType):
        node = Entrypoint(Node)
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task", project__name="Project", assignees__name="Assignee")

    global_id = to_global_id(typename=TaskType.__typename__, object_id=task.pk)

    query = """
        query NodeQuery($global_id: ID!) {
          node(id: $global_id) {
            __typename
            ... on TaskType {
              name
              project {
                name
              }
              assignees {
                name
              }
            }
          }
        }
    """

    response = graphql(query, variables={"global_id": global_id})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "node": {
            "__typename": "TaskType",
            "name": "Task",
            "project": {"name": "Project"},
            "assignees": [{"name": "Assignee"}],
        },
    }

    # 1 query for fetching the task and project
    # 1 query for fetching the assignees
    response.assert_query_count(2)


# Relay Connections


@pytest.mark.django_db
def test_optimizer__relay__connection(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__first(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(first: 1) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__last(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(last: 1) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    # 1 query for counting tasks
    # 1 query for fetching all tasks
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__after(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query ($after: String!) {
          tasks(after: $after) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    typename = TaskType.__typename__
    response = graphql(query, variables={"after": offset_to_cursor(typename, 0)})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__before(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query ($before: String!) {
          tasks(before: $before) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    typename = TaskType.__typename__
    response = graphql(query, variables={"before": offset_to_cursor(typename, 2)})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__offset(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query ($offset: Int!) {
          tasks(offset: $offset) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, variables={"offset": 1})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__connection_info(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                name
              }
            }
          }
        }
    """

    typename = TaskType.__typename__
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": offset_to_cursor(typename, 0),
                "endCursor": offset_to_cursor(typename, 2),
            },
            "edges": [
                {
                    "cursor": offset_to_cursor(typename, 0),
                    "node": {
                        "name": "Task 1",
                    },
                },
                {
                    "cursor": offset_to_cursor(typename, 1),
                    "node": {
                        "name": "Task 2",
                    },
                },
                {
                    "cursor": offset_to_cursor(typename, 2),
                    "node": {
                        "name": "Task 3",
                    },
                },
            ],
        },
    }

    # 1 query for counting all tasks
    # 1 query for fetching all tasks
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__no_max_limit(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType, max_limit=None))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__no_max_limit__first(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType, max_limit=None))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(first: 1) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__no_max_limit__last(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType, max_limit=None))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(last: 2) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    # 1 query for counting all tasks
    # 1 query for fetching all tasks
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__max_limit__has_next_page(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType, max_limit=2))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                name
              }
            }
          }
        }
    """

    typename = TaskType.__typename__
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": offset_to_cursor(typename, 0),
                "endCursor": offset_to_cursor(typename, 1),
            },
            "edges": [
                {
                    "cursor": offset_to_cursor(typename, 0),
                    "node": {
                        "name": "Task 1",
                    },
                },
                {
                    "cursor": offset_to_cursor(typename, 1),
                    "node": {
                        "name": "Task 2",
                    },
                },
            ],
        },
    }

    # 1 query for counting all tasks
    # 1 query for fetching all tasks
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__max_limit__has_previous_page(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType, max_limit=2))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query ($after: String!) {
          tasks(after: $after) {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                name
              }
            }
          }
        }
    """

    typename = TaskType.__typename__
    response = graphql(query, variables={"after": offset_to_cursor(typename, 0)})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": offset_to_cursor(typename, 1),
                "endCursor": offset_to_cursor(typename, 2),
            },
            "edges": [
                {
                    "cursor": offset_to_cursor(typename, 1),
                    "node": {
                        "name": "Task 2",
                    },
                },
                {
                    "cursor": offset_to_cursor(typename, 2),
                    "node": {
                        "name": "Task 3",
                    },
                },
            ],
        },
    }

    # 1 query for counting all tasks
    # 1 query for fetching all tasks
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__joins(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False):
        name = Field()

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        project = Field(ProjectType)
        assignees = Field(PersonType)

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project__name="Project 1", assignees__name="Assignee 1")
    TaskFactory.create(name="Task 2", project__name="Project 2", assignees__name="Assignee 2")
    TaskFactory.create(name="Task 3", project__name="Project 3", assignees__name="Assignee 3")

    query = """
        query {
          tasks {
            edges {
              node {
                name
                project {
                  name
                }
                assignees {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "project": {"name": "Project 1"},
                        "assignees": [{"name": "Assignee 1"}],
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "project": {"name": "Project 2"},
                        "assignees": [{"name": "Assignee 2"}],
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "project": {"name": "Project 3"},
                        "assignees": [{"name": "Assignee 3"}],
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks and projects
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__joins__connection_info(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False):
        name = Field()

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        project = Field(ProjectType)
        assignees = Field(PersonType)

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project__name="Project 1", assignees__name="Assignee 1")
    TaskFactory.create(name="Task 2", project__name="Project 2", assignees__name="Assignee 2")
    TaskFactory.create(name="Task 3", project__name="Project 3", assignees__name="Assignee 3")

    query = """
        query {
          tasks {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                name
                project {
                  name
                }
                assignees {
                  name
                }
              }
            }
          }
        }
    """

    typename = TaskType.__typename__
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": offset_to_cursor(typename, 0),
                "endCursor": offset_to_cursor(typename, 2),
            },
            "edges": [
                {
                    "cursor": offset_to_cursor(typename, 0),
                    "node": {
                        "name": "Task 1",
                        "project": {"name": "Project 1"},
                        "assignees": [{"name": "Assignee 1"}],
                    },
                },
                {
                    "cursor": offset_to_cursor(typename, 1),
                    "node": {
                        "name": "Task 2",
                        "project": {"name": "Project 2"},
                        "assignees": [{"name": "Assignee 2"}],
                    },
                },
                {
                    "cursor": offset_to_cursor(typename, 2),
                    "node": {
                        "name": "Task 3",
                        "project": {"name": "Project 3"},
                        "assignees": [{"name": "Assignee 3"}],
                    },
                },
            ],
        },
    }

    # 1 query for counting all tasks
    # 1 query for fetching all tasks and projects
    # 1 query for fetching all assignees
    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relay__connection__total_count_in_fragment(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        fragment TaskEdges on TaskTypeConnection {
          totalCount
          edges {
            node {
              name
            }
          }
        }

        query {
          tasks {
            ...TaskEdges
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    # 1 query for counting all tasks
    # 1 query for fetching all tasks
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__different_ordering(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node], orderset=True):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(orderBy: nameDesc, first: 2) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 3"}},
                {"node": {"name": "Task 2"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__only_total_count(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            totalCount
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
        },
    }

    # Technically we shouldn't need to fetch tasks and only do the count.
    # 1 query for counting all tasks
    # 1 query for fetching all tasks
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__only_cursor(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            edges {
              cursor
            }
          }
        }
    """

    typename = TaskType.__typename__
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"cursor": offset_to_cursor(typename, 0)},
                {"cursor": offset_to_cursor(typename, 1)},
                {"cursor": offset_to_cursor(typename, 2)},
            ],
        },
    }

    # 1 query for counting all tasks
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__alias(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            edges {
              node {
                name
              }
            }
          }
          pagedTasks: tasks(first: 1) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
        "pagedTasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching paged tasks
    response.assert_query_count(2)


# Nested Relay Connections


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__many_to_many__forward(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__many_to_many__reverse(graphql, undine_settings):
    class ReportType(QueryType, model=Report, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        reports = Field(Connection(ReportType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    report_1 = ReportFactory.create(name="Report 1")
    report_2 = ReportFactory.create(name="Report 2")
    report_3 = ReportFactory.create(name="Report 3")
    report_4 = ReportFactory.create(name="Report 4")
    report_5 = ReportFactory.create(name="Report 5")

    TaskFactory.create(name="Task 1", reports=[report_1, report_2, report_3])
    TaskFactory.create(name="Task 2", reports=[report_3, report_4])
    TaskFactory.create(name="Task 3", reports=[report_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                reports {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "reports": {
                            "edges": [
                                {"node": {"name": "Report 1"}},
                                {"node": {"name": "Report 2"}},
                                {"node": {"name": "Report 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "reports": {
                            "edges": [
                                {"node": {"name": "Report 3"}},
                                {"node": {"name": "Report 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "reports": {
                            "edges": [
                                {"node": {"name": "Report 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all reports
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__first(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(first: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__last(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(last: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__after(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query ($after: String!) {
          tasks {
            edges {
              node {
                name
                assignees(after: $after) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    typename = PersonType.__typename__
    response = graphql(query, variables={"after": offset_to_cursor(typename, 0)})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__before(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query ($before: String!) {
          tasks {
            edges {
              node {
                name
                assignees(before: $before) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    typename = PersonType.__typename__
    response = graphql(query, variables={"before": offset_to_cursor(typename, 2)})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__offset(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(offset: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__connection_info(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  totalCount
                  pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                  }
                  edges {
                    cursor
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    typename = PersonType.__typename__
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 2),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {"name": "Assignee 1"},
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 1),
                                    "node": {"name": "Assignee 2"},
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 2),
                                    "node": {"name": "Assignee 3"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 1),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {"name": "Assignee 3"},
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 1),
                                    "node": {"name": "Assignee 4"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 0),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {"name": "Assignee 5"},
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__no_max_limit(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType, max_limit=None))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__no_max_limit__first(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType, max_limit=None))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(first: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__no_max_limit__last(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType, max_limit=None))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(last: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__max_limit__has_next_page(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType, max_limit=2))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  totalCount
                  pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                  }
                  edges {
                    cursor
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    typename = PersonType.__typename__
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "pageInfo": {
                                "hasNextPage": True,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 1),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {"name": "Assignee 1"},
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 1),
                                    "node": {"name": "Assignee 2"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 1),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {"name": "Assignee 3"},
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 1),
                                    "node": {"name": "Assignee 4"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 0),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {"name": "Assignee 5"},
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__max_limit__has_previous_page(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType, max_limit=2))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query ($after: String!) {
          tasks {
            edges {
              node {
                name
                assignees(after: $after) {
                  totalCount
                  pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                  }
                  edges {
                    cursor
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    typename = PersonType.__typename__
    response = graphql(query, variables={"after": offset_to_cursor(typename, 0)})

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": True,
                                "startCursor": offset_to_cursor(typename, 1),
                                "endCursor": offset_to_cursor(typename, 2),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 1),
                                    "node": {"name": "Assignee 2"},
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 2),
                                    "node": {"name": "Assignee 3"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": True,
                                "startCursor": offset_to_cursor(typename, 1),
                                "endCursor": offset_to_cursor(typename, 1),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 1),
                                    "node": {"name": "Assignee 4"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            # Details are wrong because we didn't get any items and couldn't read the annotations
                            "totalCount": 0,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": None,
                                "endCursor": None,
                            },
                            "edges": [],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__joins(graphql, undine_settings):
    class TeamType(QueryType, model=Team, auto=False):
        name = Field()

    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()
        teams = Field(TeamType)

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    team_1 = TeamFactory.create(name="Team 1")
    team_2 = TeamFactory.create(name="Team 2")

    person_1 = PersonFactory.create(name="Assignee 1", teams=[team_1])
    person_2 = PersonFactory.create(name="Assignee 2", teams=[team_1])
    person_3 = PersonFactory.create(name="Assignee 3", teams=[team_2])
    person_4 = PersonFactory.create(name="Assignee 4", teams=[team_2])
    person_5 = PersonFactory.create(name="Assignee 5", teams=[team_1, team_2])

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                      teams {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 1",
                                        "teams": [{"name": "Team 1"}],
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 2",
                                        "teams": [{"name": "Team 1"}],
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 3",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 3",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 4",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 5",
                                        "teams": [{"name": "Team 1"}, {"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    # 1 query for fetching all teams
    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__joins__connection_info(graphql, undine_settings):
    class TeamType(QueryType, model=Team, auto=False):
        name = Field()

    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()
        teams = Field(TeamType)

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    team_1 = TeamFactory.create(name="Team 1")
    team_2 = TeamFactory.create(name="Team 2")

    person_1 = PersonFactory.create(name="Assignee 1", teams=[team_1])
    person_2 = PersonFactory.create(name="Assignee 2", teams=[team_1])
    person_3 = PersonFactory.create(name="Assignee 3", teams=[team_2])
    person_4 = PersonFactory.create(name="Assignee 4", teams=[team_2])
    person_5 = PersonFactory.create(name="Assignee 5", teams=[team_1, team_2])

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  totalCount
                  pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                  }
                  edges {
                    cursor
                    node {
                      name
                      teams {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    typename = PersonType.__typename__
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 2),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {
                                        "name": "Assignee 1",
                                        "teams": [{"name": "Team 1"}],
                                    },
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 1),
                                    "node": {
                                        "name": "Assignee 2",
                                        "teams": [{"name": "Team 1"}],
                                    },
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 2),
                                    "node": {
                                        "name": "Assignee 3",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 1),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {
                                        "name": "Assignee 3",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                                {
                                    "cursor": offset_to_cursor(typename, 1),
                                    "node": {
                                        "name": "Assignee 4",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(typename, 0),
                                "endCursor": offset_to_cursor(typename, 0),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(typename, 0),
                                    "node": {
                                        "name": "Assignee 5",
                                        "teams": [{"name": "Team 1"}, {"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    # 1 query for fetching all teams
    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__total_count_in_fragment(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        fragment Assignees on PersonTypeConnection {
          totalCount
          edges {
            node {
              name
            }
          }
        }

        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  ...Assignees
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__one_to_many(graphql, undine_settings):
    class TaskStepType(QueryType, model=TaskStep, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        steps = Field(Connection(TaskStepType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    TaskStepFactory.create(name="Task Step 1", task=task_1)
    TaskStepFactory.create(name="Task Step 2", task=task_1)
    TaskStepFactory.create(name="Task Step 3", task=task_2)
    TaskStepFactory.create(name="Task Step 4", task=task_2)
    TaskStepFactory.create(name="Task Step 5", task=task_3)

    query = """
        query {
          tasks {
            edges {
              node {
                name
                steps {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 1"}},
                                {"node": {"name": "Task Step 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 3"}},
                                {"node": {"name": "Task Step 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__one_to_many__total_count(graphql, undine_settings):
    class TaskStepType(QueryType, model=TaskStep, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        steps = Field(Connection(TaskStepType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    TaskStepFactory.create(name="Task Step 1", task=task_1)
    TaskStepFactory.create(name="Task Step 2", task=task_1)
    TaskStepFactory.create(name="Task Step 3", task=task_2)
    TaskStepFactory.create(name="Task Step 4", task=task_2)
    TaskStepFactory.create(name="Task Step 5", task=task_3)

    query = """
        query {
          tasks {
            edges {
              node {
                name
                steps {
                  totalCount
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "steps": {
                            "totalCount": 2,
                            "edges": [
                                {"node": {"name": "Task Step 1"}},
                                {"node": {"name": "Task Step 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "steps": {
                            "totalCount": 2,
                            "edges": [
                                {"node": {"name": "Task Step 3"}},
                                {"node": {"name": "Task Step 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "steps": {
                            "totalCount": 1,
                            "edges": [
                                {"node": {"name": "Task Step 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all task steps
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__different_ordering(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node], orderset=True):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(orderBy: nameDesc, first: 2) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 4"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__only_total_count(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  totalCount
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__only_cursor(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    cursor
                  }
                }
              }
            }
          }
        }
    """

    typename = PersonType.__typename__
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"cursor": offset_to_cursor(typename, 0)},
                                {"cursor": offset_to_cursor(typename, 1)},
                                {"cursor": offset_to_cursor(typename, 2)},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"cursor": offset_to_cursor(typename, 0)},
                                {"cursor": offset_to_cursor(typename, 1)},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"cursor": offset_to_cursor(typename, 0)},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__multiple_connections(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskStepType(QueryType, model=TaskStep, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))
        steps = Field(Connection(TaskStepType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    task_1 = TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    task_2 = TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    task_3 = TaskFactory.create(name="Task 3", assignees=[person_5])

    TaskStepFactory.create(name="Task Step 1", task=task_1)
    TaskStepFactory.create(name="Task Step 2", task=task_1)
    TaskStepFactory.create(name="Task Step 3", task=task_2)
    TaskStepFactory.create(name="Task Step 4", task=task_2)
    TaskStepFactory.create(name="Task Step 5", task=task_3)

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                    }
                  }
                }
                steps {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 1"}},
                                {"node": {"name": "Task Step 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 3"}},
                                {"node": {"name": "Task Step 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    # 1 query for fetching all task steps
    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__aliased_connections(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                    }
                  }
                }
                persons: assignees(first: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                        "persons": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                        "persons": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                        "persons": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    # 1 query for fetching all task steps
    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__generic_relation(graphql, undine_settings):
    class CommentType(QueryType, model=Comment, auto=False, interfaces=[Node]):
        contents = Field()

    class TaskType(QueryType, model=Task, auto=False, interfaces=[Node]):
        name = Field()
        comments = Field(Connection(CommentType))

    class Query(RootOperationType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    CommentFactory.create(contents="Comment 1", target=task_1)
    CommentFactory.create(contents="Comment 2", target=task_1)
    CommentFactory.create(contents="Comment 3", target=task_2)
    CommentFactory.create(contents="Comment 4", target=task_2)
    CommentFactory.create(contents="Comment 5", target=task_3)

    query = """
        query {
          tasks {
            edges {
              node {
                name
                comments {
                  edges {
                    node {
                      contents
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "comments": {
                            "edges": [
                                {"node": {"contents": "Comment 1"}},
                                {"node": {"contents": "Comment 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "comments": {
                            "edges": [
                                {"node": {"contents": "Comment 3"}},
                                {"node": {"contents": "Comment 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "comments": {
                            "edges": [
                                {"node": {"contents": "Comment 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all tasks
    # 1 query for fetching all assignees
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__third_level_connection(graphql, undine_settings):
    class CommentType(QueryType, model=Comment, auto=False, interfaces=[Node]):
        contents = Field()

    class PersonType(QueryType, model=Person, auto=False, interfaces=[Node]):
        name = Field()
        comments = Field(Connection(CommentType))

    class TeamType(QueryType, model=Team, auto=False, interfaces=[Node]):
        name = Field()
        members = Field(Connection(PersonType))

    class Query(RootOperationType):
        teams = Entrypoint(Connection(TeamType))

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1", project=None)
    task_2 = TaskFactory.create(name="Task 2", project=None)
    task_3 = TaskFactory.create(name="Task 3", project=None)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    CommentFactory.create(contents="Comment 1", commenter=person_1, target=task_1)
    CommentFactory.create(contents="Comment 2", commenter=person_2, target=task_1)
    CommentFactory.create(contents="Comment 3", commenter=person_2, target=task_2)
    CommentFactory.create(contents="Comment 4", commenter=person_3, target=task_2)
    CommentFactory.create(contents="Comment 5", commenter=person_3, target=task_3)
    CommentFactory.create(contents="Comment 6", commenter=person_5, target=task_3)

    TeamFactory.create(name="Team 1", members=[person_1, person_2, person_3])
    TeamFactory.create(name="Team 2", members=[person_3, person_4])
    TeamFactory.create(name="Team 3", members=[person_5])

    query = """
        query {
          teams {
            edges {
              node {
                name
                members {
                  edges {
                    node {
                      name
                      comments {
                        edges {
                          node {
                            contents
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "teams": {
            "edges": [
                {
                    "node": {
                        "name": "Team 1",
                        "members": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 1",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 1"}},
                                            ],
                                        },
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 2",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 2"}},
                                                {"node": {"contents": "Comment 3"}},
                                            ],
                                        },
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 3",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 4"}},
                                                {"node": {"contents": "Comment 5"}},
                                            ],
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Team 2",
                        "members": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 3",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 4"}},
                                                {"node": {"contents": "Comment 5"}},
                                            ],
                                        },
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 4",
                                        "comments": {
                                            "edges": [],
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Team 3",
                        "members": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 5",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 6"}},
                                            ],
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    # 1 query for fetching all teams
    # 1 query for fetching all members
    # 1 query for fetching all comments
    response.assert_query_count(3)
