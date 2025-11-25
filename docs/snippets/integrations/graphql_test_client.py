def test_example(graphql) -> None:
    query = "query { test }"

    response = graphql(query)

    assert response.data == {"hello": "Hello, World!"}
