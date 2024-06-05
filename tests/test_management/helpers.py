from __future__ import annotations

from contextlib import contextmanager
from functools import partial
from http import HTTPStatus
from typing import Any
from unittest.mock import Mock, patch

from undine.management.commands import fetch_graphiql_static_for_undine

__all__ = [
    "COMMAND_NAME",
    "MockResponse",
    "patch_requests",
]


COMMAND_NAME = fetch_graphiql_static_for_undine.__name__.split(".")[-1]


class MockResponse:
    def __init__(self, *, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.content = content
        self.status = status

    def read(self) -> bytes:
        return self.content.encode("utf-8")


class MockConnection:
    def __init__(self, host: str, *args: Any, **kwargs: Any) -> None:
        self.host = host
        self.url: str | None = None
        self.responses: dict[str, MockResponse] = kwargs.get("responses", {})

    def request(self, url: str, *args: Any, **kwargs: Any) -> None:
        self.url = url

    def getresponse(self) -> MockResponse:
        assert self.url is not None, "Mock used incorrectly. 'url' attribute is missing."

        try:
            return self.responses[self.url]

        except KeyError as error:  # pragma: no cover
            msg = f"A response for '{self.url}' has not been defined."
            raise RuntimeError(msg) from error


def get_target_path(target: str) -> str:
    assert hasattr(fetch_graphiql_static_for_undine, target), f"Mock is missing target for '{target}'!"

    return f"{fetch_graphiql_static_for_undine.__name__}.{target}"


@contextmanager
def patch_requests(responses: dict[str, MockResponse]):
    path_1 = get_target_path("HTTPSConnection")
    path_2 = get_target_path("Path")

    patch_1 = patch(path_1, side_effect=partial(MockConnection, responses=responses))
    patch_2 = patch(f"{path_2}.write_text", side_effect=Mock())

    with patch_1, patch_2 as mock:
        yield mock
