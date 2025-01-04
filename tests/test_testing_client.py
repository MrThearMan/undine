from copy import deepcopy
from inspect import cleandoc
from typing import Any

import pytest
from _pytest.outcomes import Failed  # noqa: PLC2701
from django.core.files.uploadedfile import InMemoryUploadedFile

from tests.helpers import create_mock_png, exact
from undine import Entrypoint, GQLInfo, RootOperationType, create_schema
from undine.scalars import GraphQLFile
from undine.testing.client import GraphQLClient


def test_testing_client(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def greeting(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          greeting
        }
    """

    client = GraphQLClient()

    response = client(query)
    assert response.has_errors is False
    assert response.json == {"data": {"greeting": "Hello, World!"}}
    assert response.data == {"greeting": "Hello, World!"}
    assert response.results == "Hello, World!"

    assert response.queries == []
    assert cleandoc(response.query_log) == cleandoc(
        """
        ---------------------------------------------------------------------------

        >>> Queries: (0)
        """,
    )


def test_testing_client__operation_name(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def greeting(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query Greet {
          greeting
        }
    """

    client = GraphQLClient()

    response = client(query, operation_name="Greet")
    assert response.has_errors is False


def test_testing_client__connection(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def stuff(self) -> dict[str, Any]:
            return {
                "edges": [
                    {"node": {"foo": "bar"}},
                    {"node": {"foo": "baz"}},
                ],
            }

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          stuff
        }
    """

    client = GraphQLClient()

    response = client(query)

    assert response.json == {
        "data": {
            "stuff": {
                "edges": [
                    {"node": {"foo": "bar"}},
                    {"node": {"foo": "baz"}},
                ],
            },
        },
    }
    assert response.data == {
        "stuff": {
            "edges": [
                {"node": {"foo": "bar"}},
                {"node": {"foo": "baz"}},
            ],
        },
    }
    assert response.results == {
        "edges": [
            {"node": {"foo": "bar"}},
            {"node": {"foo": "baz"}},
        ],
    }
    assert response.edges == [
        {"node": {"foo": "bar"}},
        {"node": {"foo": "baz"}},
    ]
    assert response.node(0) == {"foo": "bar"}
    assert response.node(1) == {"foo": "baz"}


def test_testing_client__error(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def greeting(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          hello
        }
    """

    client = GraphQLClient()

    response = client(query)

    assert response.has_errors is True
    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Cannot query field 'hello' on type 'Query'.",
                "extensions": {"status_code": 400},
                "locations": [{"column": 11, "line": 3}],
            },
        ],
    }
    assert response.data is None

    assert response.errors == [
        {
            "message": "Cannot query field 'hello' on type 'Query'.",
            "extensions": {"status_code": 400},
            "locations": [{"column": 11, "line": 3}],
        },
    ]

    assert response.error_message(0) == "Cannot query field 'hello' on type 'Query'."


def test_testing_client__error__no_results(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def greeting(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          hello
        }
    """

    client = GraphQLClient()

    response = client(query)

    msg = f"No query object not found in response content\nContent: {response.json}"
    with pytest.raises(Failed, match=exact(msg)):
        assert response.results


def test_testing_client__error__no_edges(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def greeting(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          greeting
        }
    """

    client = GraphQLClient()

    response = client(query)

    msg = f"Edges not found in response content\nContent: {response.json}"
    with pytest.raises(Failed, match=exact(msg)):
        assert response.edges


def test_testing_client__error__no_node(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def stuff(self) -> dict[str, Any]:
            return {
                "edges": [
                    {"node": {"foo": "bar"}},
                    {"node": {"foo": "baz"}},
                ],
            }

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          stuff
        }
    """

    client = GraphQLClient()

    response = client(query)

    msg = f"Node 3 not found in response content\nContent: {response.json}"
    with pytest.raises(Failed, match=exact(msg)):
        assert response.node(3)


def test_testing_client__error__no_error_message__index(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def greeting(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          hello
        }
    """

    client = GraphQLClient()

    response = client(query)

    msg = f"Errors message not found from index 1\nContent: {response.json}"
    with pytest.raises(Failed, match=exact(msg)):
        assert response.error_message(1)


def test_testing_client__error__no_error_message__path(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def greeting(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          hello
        }
    """

    client = GraphQLClient()

    response = client(query)

    msg = f"Errors message not found from path 'foo'\nContent: {response.json}"
    with pytest.raises(Failed, match=exact(msg)):
        assert response.error_message("foo")


def test_testing_client__assert_query_count(undine_settings):
    class Query(RootOperationType):
        @Entrypoint
        def greeting(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          hello
        }
    """

    client = GraphQLClient()

    response = client(query)

    response.assert_query_count(0)

    msg = (
        "Expected 1 queries, got 0.\n"
        "\n"
        "---------------------------------------------------------------------------\n"
        "\n"
        ">>> Queries: (0)"
    )
    with pytest.raises(Failed, match=exact(msg)):
        response.assert_query_count(1)


@pytest.mark.django_db
def test_testing_client__login_with_superuser(undine_settings):
    request_user = None

    class Query(RootOperationType):
        @Entrypoint
        def greeting(self, info: GQLInfo) -> str:
            nonlocal request_user
            request_user = info.context.user
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          greeting
        }
    """

    client = GraphQLClient()
    user = client.login_with_superuser()
    assert user.is_superuser is True
    assert user.is_staff is True

    response = client(query)
    assert response.has_errors is False

    assert request_user == user


@pytest.mark.django_db
def test_testing_client__login_with_regular_user(undine_settings):
    request_user = None

    class Query(RootOperationType):
        @Entrypoint
        def greeting(self, info: GQLInfo) -> str:
            nonlocal request_user
            request_user = info.context.user
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          greeting
        }
    """

    client = GraphQLClient()
    user = client.login_with_regular_user()
    assert user.is_superuser is False
    assert user.is_staff is False

    response = client(query)
    assert response.has_errors is False

    assert request_user == user


def test_testing_client__files(undine_settings):
    captured: InMemoryUploadedFile | None = None

    class Query(RootOperationType):
        @Entrypoint
        def greeting(self, file: GraphQLFile) -> str:
            nonlocal captured
            captured = deepcopy(file)
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    png = create_mock_png()
    png_bytes = bytes(png.file.read())
    png.file.seek(0)

    query = """
        query ($file: File!) {
          greeting(file: $file)
        }
    """

    client = GraphQLClient()

    response = client(query, variables={"file": png})
    assert response.has_errors is False

    assert isinstance(captured, InMemoryUploadedFile)
    assert captured.name == "image.png"
    assert captured.size == png.size
    assert captured.content_type == "image/png"
    assert captured.charset is None

    assert bytes(captured.read()) == png_bytes
