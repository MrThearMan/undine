from __future__ import annotations

import asyncio

import pytest
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLError, GraphQLErrorGroup


@pytest.mark.django_db
def test_end_to_end__field_errors__validation_error__nullable(graphql, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def example(self) -> str | None:
            msg = "Invalid value."
            raise ValidationError(msg, code="invalid")

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { example }")

    assert response.json == {
        "data": {"example": None},
        "errors": [
            {
                "message": "Invalid value.",
                "path": ["example"],
                "extensions": {"status_code": 400, "error_code": "INVALID"},
            },
        ],
    }


@pytest.mark.django_db
def test_end_to_end__field_errors__validation_error__nullable__multiple_messages(graphql, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def example(self) -> str | None:
            raise ValidationError(["First error.", "Second error."])

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { example }")

    assert response.json == {
        "data": {"example": None},
        "errors": [
            {
                "message": "First error.",
                "path": ["example"],
                "extensions": {"status_code": 400},
            },
            {
                "message": "Second error.",
                "path": ["example"],
                "extensions": {"status_code": 400},
            },
        ],
    }


@pytest.mark.django_db
def test_end_to_end__field_errors__error_group__nullable(graphql, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def example(self, info: GQLInfo) -> str | None:
            errors = [
                GraphQLError("First error."),
                GraphQLError("Second error.", nodes=info.field_nodes, path=["other"]),
            ]
            raise GraphQLErrorGroup(errors)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { example }")

    assert response.json == {
        "data": {"example": None},
        "errors": [
            {
                "message": "First error.",
                "path": ["example"],
                "extensions": {"status_code": 400},
            },
            {
                "message": "Second error.",
                "path": ["other"],
                "extensions": {"status_code": 400},
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_end_to_end__field_errors__error_group__non_null__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Query(RootType):
        @Entrypoint
        async def example(self) -> str:
            errors = [GraphQLError("First error."), GraphQLError("Second error.")]
            raise GraphQLErrorGroup(errors)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async("query { example }")

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "First error.",
                "path": ["example"],
                "extensions": {"status_code": 400},
            },
            {
                "message": "Second error.",
                "path": ["example"],
                "extensions": {"status_code": 400},
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_end_to_end__field_errors__error_group__parent_already_nulled__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    sibling_failed = asyncio.Event()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def late(self: Task) -> str | None:
            await sibling_failed.wait()
            await asyncio.sleep(0.01)
            errors = [GraphQLError("First late error."), GraphQLError("Second late error.")]
            raise GraphQLErrorGroup(errors)

        @Field
        async def early(self: Task) -> str:
            sibling_failed.set()
            msg = "Early error."
            raise GraphQLError(msg)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True, nullable=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo")

    response = await graphql_async("query { tasks { name late early } }")

    assert response.json == {
        "data": {"tasks": None},
        "errors": [
            {
                "message": "Early error.",
                "path": ["tasks", 0, "early"],
                "extensions": {"status_code": 400},
            },
        ],
    }
