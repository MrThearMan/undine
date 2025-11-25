def test_example(graphql) -> None:
    query = "query { test { edges { node { id } } } }"

    response = graphql(query, count_queries=True)

    # The whole response
    assert response.json == {
        "data": {"test": {"edges": [{"node": {"id": "1"}}]}},
        "errors": [{"message": "Error message", "path": ["test"]}],
    }

    # Error properties
    assert response.has_errors is True
    assert response.errors == [{"message": "Error message", "path": ["test"]}]
    assert response.error_message(0) == "Error message"

    # Data properties
    assert response.data == {"test": {"edges": [{"node": {"id": "1"}}]}}
    assert response.results == {"edges": [{"node": {"id": "1"}}]}

    # Connection specific properties
    assert response.edges == [{"node": {"id": "1"}}]
    assert response.node(0) == {"id": "1"}

    # Check queries (requires `count_queries=True`)
    assert response.query_count == 1
    assert response.queries == ["SELECT 1;"]
    response.assert_query_count(1)
