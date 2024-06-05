from __future__ import annotations

import pytest
from graphql import GraphQLError

from example_project.app.models import Task
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.exceptions import UndineErrorGroup
from undine.relay import Node


@pytest.mark.django_db
def test_schema_validation__id_not_global_id(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    with pytest.raises(UndineErrorGroup) as exc_info:
        create_schema(query=Query)

    assert len(exc_info.value.exceptions) == 1

    exception = exc_info.value.exceptions[0]
    assert isinstance(exception, GraphQLError)
    assert exception.message == "Interface field Node.id expects type ID! but TaskType.id is type Int!."
