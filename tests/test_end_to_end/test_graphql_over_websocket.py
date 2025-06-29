from __future__ import annotations

import pytest

from undine import Entrypoint, RootType, create_schema

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),  # For sessions
]


async def test_graphql_over_websocket(graphql, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { test }"

    async for response in graphql.over_websocket(query):
        assert response.data == {"test": "Hello, World!"}
