from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from django.contrib.auth import get_user_model
from django.test.client import MULTIPART_CONTENT, Client

from undine.http.files import extract_files
from undine.persisted_documents.utils import to_document_id
from undine.settings import undine_settings

from .query_logging import capture_database_queries

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.core.files import File

    from undine.typing import DjangoTestClientHttpResponseProtocol

    from .query_logging import DBQueryData


__all__ = [
    "GraphQLClient",
    "GraphQLClientResponse",
]


class GraphQLClient(Client):
    """A GraphQL client for testing."""

    def __call__(
        self,
        document: str,
        *,
        variables: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        operation_name: str | None = None,
        use_persisted_document: bool = False,
    ) -> GraphQLClientResponse:
        """
        Execute a GraphQL operation.

        :param document: GraphQL document string to send in the request.
        :param variables: GraphQL variables for the document.
        :param headers: Headers for the request.
        :param operation_name: If given document includes multiple operations,
                               this is required to select the operation to execute.
        :param use_persisted_document: Instead of sending the whole document,
                                       convert it to a persisted document ID and send that.
        """
        variables = variables or {}
        body: dict[str, Any] = {}

        if use_persisted_document:
            body["documentId"] = to_document_id(document)
        else:
            body["query"] = document

        if variables:
            body["variables"] = variables
        if operation_name is not None:
            body["operationName"] = operation_name

        files = extract_files(variables)
        data = self._create_multipart_data(body, files) if files else body
        content_type = MULTIPART_CONTENT if files else "application/json"

        with capture_database_queries() as results:
            response = self._graphql_request(data, content_type, headers)

        return GraphQLClientResponse(response, results)

    query = __call__
    mutation = __call__

    def login_with_superuser(self, username: str = "admin", **kwargs: Any) -> User:
        """Create a superuser and log in as that user."""
        defaults = {
            "is_staff": True,
            "is_superuser": True,
            "email": "superuser@django.com",
            **kwargs,
        }
        user, _ = get_user_model().objects.get_or_create(username=username, defaults=defaults)
        self.force_login(user)
        return user

    def login_with_regular_user(self, username: str = "user", **kwargs: Any) -> User:
        """Create a regular user and log in as that user."""
        defaults = {
            "is_staff": False,
            "is_superuser": False,
            "email": "user@django.com",
            **kwargs,
        }
        user, _ = get_user_model().objects.get_or_create(username=username, defaults=defaults)
        self.force_login(user)
        return user

    def _graphql_request(
        self,
        data: dict[str, Any],
        content_type: str = "application/json",
        headers: dict[str, Any] | None = None,
    ) -> DjangoTestClientHttpResponseProtocol:
        return self.post(  # type: ignore[return-value]
            path=f"/{undine_settings.GRAPHQL_PATH}",
            data=data,
            content_type=content_type,
            headers=headers,
        )

    def _create_multipart_data(self, body: dict[str, Any], files: dict[File, list[str]]) -> dict[str, Any]:
        path_map: dict[str, list[str]] = {}
        files_map: dict[str, File] = {}
        for i, (file, path) in enumerate(files.items()):
            path_map[str(i)] = path
            files_map[str(i)] = file

        return {
            "operations": json.dumps(body),
            "map": json.dumps(path_map),
            **files_map,
        }


class GraphQLClientResponse:
    """A response from a GraphQL client."""

    def __init__(self, response: DjangoTestClientHttpResponseProtocol, database_queries: DBQueryData) -> None:
        self.response = response
        self.database_queries = database_queries

    def __str__(self) -> str:
        return json.dumps(self.json, indent=2, sort_keys=True, default=str)

    def __repr__(self) -> str:
        return repr(self.json)

    def __getitem__(self, item: str) -> dict[str, Any] | None:
        return self.json[item]

    def __contains__(self, item: str) -> bool:
        return item in self.json

    @property
    def queries(self) -> list[str]:
        """Return a list of the database queries that were executed."""
        return [info.sql for info in self.database_queries.queries]

    @property
    def query_count(self) -> int:
        """Return the number of database queries that were executed."""
        return self.database_queries.count

    @property
    def query_log(self) -> str:
        """Return a string representation of the database queries that were executed."""
        return self.database_queries.log

    @property
    def status_code(self) -> int:
        """Return the status code of the response."""
        return self.response.status_code

    @property
    def json(self) -> dict[str, Any]:
        """Return the JSON content of the response."""
        return self.response.json()

    @property
    def data(self) -> dict[str, Any] | None:
        """Return the data from the response content."""
        return self.json["data"]

    @property
    def results(self) -> dict[str, Any] | list[Any] | None:
        """
        Return the results from the first top-level field in the response content.

        >>> self.json
        {"data": {"foo": {"name": "bar"}}}
        >>> self.results
        {"name": "bar"}
        """
        data = self.data or {}
        try:
            return next(iter(data.values()))
        except StopIteration:
            msg = f"No query object not found in response content\nContent: {self.json}"
            return pytest.fail(msg, pytrace=False)

    @property
    def edges(self) -> list[dict[str, Any]]:
        """
        Return edges from the first top-level field in the response content.

        >>> self.json
        {"data": {"foo": {"edges": [{"node": {"name": "bar"}}]}}}
        >>> self.edges
        [{"node": {"name": "bar"}}]
        """
        results = self.results
        if not isinstance(results, dict):
            msg = f"Edges not found in response content\nContent: {self.json}"
            return pytest.fail(msg, pytrace=False)

        try:
            return results["edges"]
        except (KeyError, TypeError):
            msg = f"Edges not found in response content\nContent: {self.json}"
            return pytest.fail(msg, pytrace=False)

    def node(self, index: int) -> dict[str, Any]:
        """
        Return the node at the given index in the response content edges.

        >>> self.json
        {"data": {"foo": {"edges": [{"node": {"name": "bar"}}]}}}
        >>> self.node(0)
        {"name": "bar"}
        """
        try:
            return self.edges[index]["node"]
        except (IndexError, TypeError):
            msg = f"Node {index!r} not found in response content\nContent: {self.json}"
            return pytest.fail(msg, pytrace=False)

    @property
    def has_errors(self) -> bool:
        """Are there any errors in the response?"""
        return "errors" in self.json and self.json.get("errors") is not None

    @property
    def errors(self) -> list[dict[str, Any]]:
        """
        Return all errors.

        >>> self.json
        {"errors": [{"message": "bar", "path": [...], ...}]}
        >>> self.errors
        [{"message": "bar", "path": [...], ...}]
        """
        try:
            return self.json["errors"]
        except (KeyError, TypeError):
            msg = f"Errors not found in response content\nContent: {self.json}"
            return pytest.fail(msg, pytrace=False)

    def error_message(self, selector: int | str) -> str:
        """
        Return the error message from the errors list...

        1) in the given index

        >>> self.json
        {"errors": [{"message": "bar", ...}]}
        >>> self.error_message(0)
        "bar"

        2) in the given path:

        >>> self.json
        {"errors": [{"message": "bar", "path": ["fizz", "buzz", "foo"], ...}]}
        >>> self.error_message("foo")
        "bar"
        """
        if isinstance(selector, int):
            try:
                return self.errors[selector]["message"]
            except (IndexError, KeyError, TypeError):
                msg = f"Errors message not found from index {selector}\nContent: {self.json}"
                return pytest.fail(msg, pytrace=False)
        else:
            try:
                return next(error["message"] for error in self.errors if error["path"][-1] == selector)
            except (StopIteration, KeyError, TypeError):
                msg = f"Errors message not found from path {selector!r}\nContent: {self.json}"
                return pytest.fail(msg, pytrace=False)

    def assert_query_count(self, count: int) -> None:
        if self.query_count != count:
            msg = f"Expected {count} queries, got {self.query_count}.\n{self.query_log}"
            pytest.fail(msg, pytrace=False)
