def test_example(graphql) -> None:
    mutation = "mutation($input: TestInput!) { test(input: $input) }"
    data = {"name": "World"}

    response = graphql(mutation, variables={"input": data})

    assert response.data == {"hello": "Hello, World!"}
