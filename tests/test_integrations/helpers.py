from __future__ import annotations

from typing import Any, Protocol
from unittest.mock import AsyncMock

from asgiref.typing import ASGIVersions, HTTPScope

from undine.integrations.channels import GraphQLSSERouter


def make_scope(
    *,
    path: str | None = None,
    method: str = "GET",
    http_version: str = "1.1",
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
) -> HTTPScope:
    if path is None:
        from undine.settings import undine_settings  # noqa: PLC0415

        path = "/" + undine_settings.GRAPHQL_PATH.removeprefix("/").removesuffix("/") + "/"

    return HTTPScope(
        type="http",
        asgi=ASGIVersions(version="3.0", spec_version="1.0"),
        http_version=http_version,
        method=method,
        path=path,
        raw_path=path.encode(),
        root_path="",
        scheme="http",
        query_string=query_string,
        headers=headers or [],
        server=("localhost", 8000),
        extensions=None,
        client=None,
    )


class MockedRouter(Protocol):
    asgi_application: AsyncMock
    sse_application: AsyncMock

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None: ...


def get_router() -> MockedRouter:
    asgi_app = AsyncMock(spec=["__call__"])
    sse_app = AsyncMock(spec=["__call__"])
    return GraphQLSSERouter(asgi_application=asgi_app, sse_application=sse_app)  # type: ignore[return-value]
