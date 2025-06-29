import pytest


@pytest.mark.asyncio  # Requires the `pytest-asyncio` plugin
@pytest.mark.django_db(transaction=True)  # For sessions
async def test_graphql(graphql) -> None:
    # Setup...

    query = "query { test }"
    async for result in graphql.over_websocket(query):
        assert result["data"] == {"test": "Hello, World!"}
