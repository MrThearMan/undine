def test_graphql(graphql) -> None:
    # Setup...

    query = "query { test }"
    response = graphql(query)
    assert response.data == {"hello": "Hello, World!"}
