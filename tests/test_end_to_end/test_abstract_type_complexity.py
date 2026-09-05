from __future__ import annotations

from typing import NamedTuple

import pytest

from tests.helpers import parametrize_helper, skip_if_union_queryset_values_broken
from tests.test_end_to_end.helpers import (
    create_interface_member_schema,
    create_one_row_per_member,
    create_union_member_schema,
)


class ComplexityParams(NamedTuple):
    selection: str
    fragments: str
    query_count: int
    complexity: int


MEMBER_CASES: dict[str, ComplexityParams] = {
    "no member selected": ComplexityParams(
        selection="{ __typename }",
        fragments="",
        query_count=0,
        complexity=1,
    ),
    "member selects its typename only": ComplexityParams(
        selection="{ ... on TaskType { __typename } }",
        fragments="",
        query_count=0,
        complexity=1,
    ),
    "one member selected": ComplexityParams(
        selection="{ ... on TaskType { done } }",
        fragments="",
        query_count=2,
        complexity=2,
    ),
    "one member selected through a fragment": ComplexityParams(
        selection="{ ...TaskFields }",
        fragments="fragment TaskFields on TaskType { done }",
        query_count=2,
        complexity=2,
    ),
    "one member selected through a fragment inside a fragment": ComplexityParams(
        selection="{ ... on TaskType { ...TaskFields } }",
        fragments="fragment TaskFields on TaskType { done }",
        query_count=2,
        complexity=2,
    ),
    "one member selected through an inline fragment inside a fragment": ComplexityParams(
        selection="{ ... on TaskType { ... on TaskType { done } } }",
        fragments="",
        query_count=2,
        complexity=2,
    ),
    "member fragment mixes typenames, empty fragments and a field": ComplexityParams(
        selection="{ ... on TaskType { __typename ...TypenameFields ... on TaskType { __typename } done } }",
        fragments="fragment TypenameFields on TaskType { __typename }",
        query_count=2,
        complexity=2,
    ),
    "two members selected, third one left out": ComplexityParams(
        selection="{ ... on TaskType { done } ... on ProjectType { name } }",
        fragments="",
        query_count=3,
        complexity=3,
    ),
    "every member selected": ComplexityParams(
        selection="{ ... on TaskType { done } ... on ProjectType { name } ... on ReportType { name } }",
        fragments="",
        query_count=4,
        complexity=4,
    ),
}

INTERFACE_FIELD_CASES: dict[str, ComplexityParams] = {
    "interface field selects every implementation": ComplexityParams(
        selection="{ name }",
        fragments="",
        query_count=4,
        complexity=4,
    ),
    "interface field next to a fragment for one implementation": ComplexityParams(
        selection="{ name ... on TaskType { done } }",
        fragments="",
        query_count=4,
        complexity=4,
    ),
    "interface field inside a fragment on the interface": ComplexityParams(
        selection="{ ... on Named { name } }",
        fragments="",
        query_count=4,
        complexity=4,
    ),
}


def assert_complexity(graphql, undine_settings, *, query: str, query_count: int, complexity: int) -> None:
    """The operation runs the expected number of queries, and is counted at the expected complexity."""
    undine_settings.MAX_QUERY_COMPLEXITY = complexity

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors
    response.assert_query_count(query_count)

    undine_settings.MAX_QUERY_COMPLEXITY = complexity - 1

    response = graphql(query)
    assert response.errors == [
        {
            "message": (
                f"Query complexity of {complexity} exceeds the maximum allowed complexity of {complexity - 1}."
            ),
            "extensions": {"status_code": 400},
        }
    ]


# Union types


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
@pytest.mark.parametrize(**parametrize_helper(MEMBER_CASES))
def test_union_type__complexity__list(  # ruff: ignore[too-many-positional-arguments]
    graphql,
    undine_settings,
    selection: str,
    fragments: str,
    query_count: int,
    complexity: int,
) -> None:
    undine_settings.SCHEMA = create_union_member_schema()
    create_one_row_per_member()

    query = f"query {{ commentables {selection} }} {fragments}"
    assert_complexity(graphql, undine_settings, query=query, query_count=query_count, complexity=complexity)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
@pytest.mark.parametrize(**parametrize_helper(MEMBER_CASES))
def test_union_type__complexity__connection(  # ruff: ignore[too-many-positional-arguments]
    graphql,
    undine_settings,
    selection: str,
    fragments: str,
    query_count: int,
    complexity: int,
) -> None:
    undine_settings.SCHEMA = create_union_member_schema()
    create_one_row_per_member()

    query = f"query {{ commentable {{ edges {{ node {selection} }} }} }} {fragments}"
    assert_complexity(graphql, undine_settings, query=query, query_count=query_count, complexity=complexity)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_union_type__complexity__connection__total_count(graphql, undine_settings) -> None:
    """The count over the selected members is an extra query, but is not counted towards the complexity."""
    undine_settings.SCHEMA = create_union_member_schema()
    create_one_row_per_member()

    query = "query { commentable { totalCount edges { node { ... on TaskType { done } } } } }"
    assert_complexity(graphql, undine_settings, query=query, query_count=3, complexity=2)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_union_type__complexity__undefined_fragment(graphql, undine_settings) -> None:
    """An undefined fragment selects no members, and is reported by the fragment validation rules."""
    undine_settings.SCHEMA = create_union_member_schema()
    undine_settings.MAX_QUERY_COMPLEXITY = 1

    query = "query { commentables { ...UndefinedFields } }"

    response = graphql(query)
    assert response.errors == [
        {
            "message": "Unknown fragment 'UndefinedFields'.",
            "extensions": {"status_code": 400},
        }
    ]


# Interface types


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
@pytest.mark.parametrize(**parametrize_helper(MEMBER_CASES | INTERFACE_FIELD_CASES))
def test_interface_type__complexity__list(  # ruff: ignore[too-many-positional-arguments]
    graphql,
    undine_settings,
    selection: str,
    fragments: str,
    query_count: int,
    complexity: int,
) -> None:
    undine_settings.SCHEMA = create_interface_member_schema()
    create_one_row_per_member()

    query = f"query {{ nameds {selection} }} {fragments}"
    assert_complexity(graphql, undine_settings, query=query, query_count=query_count, complexity=complexity)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
@pytest.mark.parametrize(**parametrize_helper(MEMBER_CASES | INTERFACE_FIELD_CASES))
def test_interface_type__complexity__connection(  # ruff: ignore[too-many-positional-arguments]
    graphql,
    undine_settings,
    selection: str,
    fragments: str,
    query_count: int,
    complexity: int,
) -> None:
    undine_settings.SCHEMA = create_interface_member_schema()
    create_one_row_per_member()

    query = f"query {{ named {{ edges {{ node {selection} }} }} }} {fragments}"
    assert_complexity(graphql, undine_settings, query=query, query_count=query_count, complexity=complexity)


@skip_if_union_queryset_values_broken
@pytest.mark.django_db
def test_interface_type__complexity__connection__total_count(graphql, undine_settings) -> None:
    """The count over the selected members is an extra query, but is not counted towards the complexity."""
    undine_settings.SCHEMA = create_interface_member_schema()
    create_one_row_per_member()

    query = "query { named { totalCount edges { node { ... on TaskType { done } } } } }"
    assert_complexity(graphql, undine_settings, query=query, query_count=3, complexity=2)
