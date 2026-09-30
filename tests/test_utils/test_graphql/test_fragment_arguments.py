from __future__ import annotations

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.utils.graphql.fragment_arguments import get_fragment_variable_values


@pytest.mark.django_db
def test_get_fragment_variable_values__field_in_list(graphql, undine_settings) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        def scope(self: Task, info: GQLInfo, value: str) -> str:
            fragment_variable_values = get_fragment_variable_values(info)
            assert fragment_variable_values is not None
            return str(fragment_variable_values.coerced)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")

    query = """
        query {
          tasks {
            ...NameFields
            ...ScopeFields(value: "bar")
          }
        }

        fragment NameFields on TaskType {
          name
        }

        fragment ScopeFields($value: String!) on TaskType {
          scope(value: $value)
        }
    """

    response = graphql(query)

    assert response.json == {"data": {"tasks": [{"name": "foo", "scope": "{'value': 'bar'}"}]}}
