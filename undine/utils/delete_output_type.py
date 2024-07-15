from graphql import GraphQLBoolean, GraphQLField, GraphQLObjectType

__all__ = [
    "DeleteMutationOutputType",
]


DeleteMutationOutputType = GraphQLObjectType(
    name="DeleteMutationOutput",
    fields={"success": GraphQLField(GraphQLBoolean)},
)
