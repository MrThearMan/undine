from __future__ import annotations

from enum import StrEnum

import pytest
from graphql import GraphQLSchema

from undine import Entrypoint, RootType, create_schema


class Color(StrEnum):
    RED = "red"
    BLUE = "blue"


def create_example_schema() -> GraphQLSchema:
    class Query(RootType):
        @Entrypoint
        def name(self) -> str:
            return "foo"

        @Entrypoint
        def color(self, value: Color) -> str:
            return value.value

    return create_schema(query=Query)


@pytest.mark.django_db
def test_did_you_mean__validation__allowed(graphql, undine_settings) -> None:
    undine_settings.ALLOW_DID_YOU_MEAN_SUGGESTIONS = True
    undine_settings.SCHEMA = create_example_schema()

    response = graphql("query { nam }")

    assert response.errors == [
        {
            "message": "Cannot query field 'nam' on type 'Query'. Did you mean 'name'?",
            "extensions": {"status_code": 400},
        },
    ]


@pytest.mark.django_db
def test_did_you_mean__validation__not_allowed(graphql, undine_settings) -> None:
    undine_settings.ALLOW_DID_YOU_MEAN_SUGGESTIONS = False
    undine_settings.SCHEMA = create_example_schema()

    response = graphql("query { nam }")

    assert response.errors == [
        {
            "message": "Cannot query field 'nam' on type 'Query'.",
            "extensions": {"status_code": 400},
        },
    ]


@pytest.mark.django_db
def test_did_you_mean__variable_coercion__allowed(graphql, undine_settings) -> None:
    undine_settings.ALLOW_DID_YOU_MEAN_SUGGESTIONS = True
    undine_settings.SCHEMA = create_example_schema()

    response = graphql("query ($value: Color!) { color(value: $value) }", variables={"value": "RDE"})

    assert response.errors == [
        {
            "message": (
                "Variable '$value' has invalid value: Value 'RDE' does not exist in 'Color' enum. "
                "Did you mean the enum value 'red'?"
            ),
            "extensions": {"status_code": 400},
        },
    ]


@pytest.mark.django_db
def test_did_you_mean__variable_coercion__not_allowed(graphql, undine_settings) -> None:
    undine_settings.ALLOW_DID_YOU_MEAN_SUGGESTIONS = False
    undine_settings.SCHEMA = create_example_schema()

    response = graphql("query ($value: Color!) { color(value: $value) }", variables={"value": "RDE"})

    assert response.errors == [
        {
            "message": "Variable '$value' has invalid value: Value 'RDE' does not exist in 'Color' enum.",
            "extensions": {"status_code": 400},
        },
    ]
