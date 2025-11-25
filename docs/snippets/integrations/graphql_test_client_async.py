import pytest


@pytest.mark.asyncio  # Requires the `pytest-asyncio` plugin
@pytest.mark.django_db(transaction=True)  # For sessions
async def test_example(graphql_async) -> None:
    query = "query { test }"

    response = await graphql_async(query)

    assert response.data == {"hello": "Hello, World!"}
