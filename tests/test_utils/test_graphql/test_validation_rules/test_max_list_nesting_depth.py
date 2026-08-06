from __future__ import annotations

import pytest

from tests.test_utils.test_graphql.test_validation_rules.helpers import (
    create_list_nesting_connection_schema,
    create_list_nesting_schema,
)


def test_validation_rules__max_list_nesting_depth(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 1
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                relatedTasks {
                    name
                }
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "List nesting depth of 2 exceeds the maximum allowed list nesting depth of 1.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__max_list_nesting_depth__at_limit(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 2
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                relatedTasks {
                    name
                }
            }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


def test_validation_rules__max_list_nesting_depth__deeply_nested(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 3
    undine_settings.MAX_QUERY_COMPLEXITY = 100
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                relatedTasks {
                    relatedTasks {
                        relatedTasks {
                            name
                        }
                    }
                }
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "List nesting depth of 4 exceeds the maximum allowed list nesting depth of 3.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__max_list_nesting_depth__to_one_relations_not_counted(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 1
    undine_settings.MAX_QUERY_COMPLEXITY = 100
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                project {
                    team {
                        name
                    }
                }
                result {
                    task {
                        result {
                            details
                        }
                    }
                }
            }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_validation_rules__max_list_nesting_depth__to_many_behind_to_one(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 2
    undine_settings.MAX_QUERY_COMPLEXITY = 100
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                project {
                    team {
                        members {
                            name
                        }
                    }
                }
            }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_validation_rules__max_list_nesting_depth__list_of_scalars_not_counted(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 1
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                tags
            }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_validation_rules__max_list_nesting_depth__siblings_do_not_accumulate(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 2
    undine_settings.MAX_QUERY_COMPLEXITY = 100
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                assignees {
                    name
                }
                relatedTasks {
                    name
                }
            }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_validation_rules__max_list_nesting_depth__sibling_entrypoints_do_not_accumulate(
    graphql,
    undine_settings,
) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 1
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                name
            }
            people {
                name
            }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


def test_validation_rules__max_list_nesting_depth__connection(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 1
    undine_settings.MAX_QUERY_COMPLEXITY = 100
    undine_settings.SCHEMA = create_list_nesting_connection_schema()

    query = """
        query {
            tasks {
                edges {
                    node {
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
    assert response.errors == [
        {
            "message": "List nesting depth of 2 exceeds the maximum allowed list nesting depth of 1.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_list_nesting_depth__fragment_spread(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 1
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        fragment RelatedTasks on TaskType {
            relatedTasks {
                name
            }
        }
        query {
            tasks {
                ...RelatedTasks
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "List nesting depth of 2 exceeds the maximum allowed list nesting depth of 1.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__max_list_nesting_depth__fragment_spread__reused(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 2
    undine_settings.MAX_QUERY_COMPLEXITY = 100
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        fragment TaskNames on TaskType {
            name
            relatedTasks {
                name
            }
        }
        query {
            tasks {
                ...TaskNames
                assignees {
                    name
                }
            }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


def test_validation_rules__max_list_nesting_depth__fragment_spread__not_found(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 100
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                ...UndefinedFrag
            }
        }
    """

    response = graphql(query)
    assert response.has_errors is True


def test_validation_rules__max_list_nesting_depth__inline_fragment(graphql, undine_settings) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 1
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                ... on TaskType {
                    relatedTasks {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "List nesting depth of 2 exceeds the maximum allowed list nesting depth of 1.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_rules__max_list_nesting_depth__inline_fragment__no_type_condition(
    graphql,
    undine_settings,
) -> None:
    undine_settings.MAX_LIST_NESTING_DEPTH = 1
    undine_settings.SCHEMA = create_list_nesting_schema()

    query = """
        query {
            tasks {
                ... {
                    relatedTasks {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query)
    assert response.errors == [
        {
            "message": "List nesting depth of 2 exceeds the maximum allowed list nesting depth of 1.",
            "extensions": {"status_code": 400},
        }
    ]
