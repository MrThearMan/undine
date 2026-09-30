from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from undine import Entrypoint, RootType, create_schema
from undine.exceptions import GraphQLError, GraphQLErrorGroup


@pytest.mark.django_db
def test_disable_error_propagation(graphql, undine_settings) -> None:
    undine_settings.EXPERIMENTAL_DISABLE_ERROR_PROPAGATION = True

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

        @Entrypoint
        def broken(self) -> str:
            msg = "Broken."
            raise GraphQLError(msg)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query @experimental_disableErrorPropagation { example broken }")

    assert response.json == {
        "data": {"example": "foo", "broken": None},
        "errors": [
            {
                "message": "Broken.",
                "path": ["broken"],
                "extensions": {"status_code": 400},
            },
        ],
    }


@pytest.mark.django_db
def test_disable_error_propagation__error_group(graphql, undine_settings) -> None:
    undine_settings.EXPERIMENTAL_DISABLE_ERROR_PROPAGATION = True

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

        @Entrypoint
        def broken(self) -> str:
            errors = [GraphQLError("First error."), GraphQLError("Second error.")]
            raise GraphQLErrorGroup(errors)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query @experimental_disableErrorPropagation { example broken }")

    assert response.json == {
        "data": {"example": "foo", "broken": None},
        "errors": [
            {
                "message": "First error.",
                "path": ["broken"],
                "extensions": {"status_code": 400},
            },
            {
                "message": "Second error.",
                "path": ["broken"],
                "extensions": {"status_code": 400},
            },
        ],
    }


@pytest.mark.django_db
def test_disable_error_propagation__validation_error(graphql, undine_settings) -> None:
    undine_settings.EXPERIMENTAL_DISABLE_ERROR_PROPAGATION = True

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

        @Entrypoint
        def broken(self) -> str:
            raise ValidationError(["First error.", "Second error."])

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query @experimental_disableErrorPropagation { example broken }")

    assert response.json == {
        "data": {"example": "foo", "broken": None},
        "errors": [
            {
                "message": "First error.",
                "path": ["broken"],
                "extensions": {"status_code": 400},
            },
            {
                "message": "Second error.",
                "path": ["broken"],
                "extensions": {"status_code": 400},
            },
        ],
    }


@pytest.mark.django_db
def test_disable_error_propagation__not_enabled(graphql, undine_settings) -> None:
    undine_settings.EXPERIMENTAL_DISABLE_ERROR_PROPAGATION = False

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query @experimental_disableErrorPropagation { example }")

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Unknown directive '@experimental_disableErrorPropagation'.",
                "extensions": {"status_code": 400},
            },
        ],
    }
