def test_graphql(graphql) -> None:
    # Setup goes here...

    query = """
        query {
          hello
        }
    """

    response = graphql(query)

    assert response.data == {"hello": "Hello, World!"}
