import pytest


@pytest.mark.asyncio  # Requires the `pytest-asyncio` plugin
@pytest.mark.django_db(transaction=True)  # For sessions
async def test_graphql(graphql) -> None:
    query = "query { test }"
    async for response in graphql.over_websocket(query):
        assert response.data == {"test": "Hello, World!"}
