from typing import Any

from graphql import GraphQLField, GraphQLInt, GraphQLNonNull, GraphQLObjectType

from undine import GQLInfo, MutationType
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type

from .models import Task


class TaskMutation(MutationType[Task]):
    @classmethod
    def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
        return {"foo": 1}

    @classmethod
    def __output_type__(cls) -> GraphQLObjectType:
        fields = {"foo": GraphQLField(GraphQLNonNull(GraphQLInt))}
        return get_or_create_graphql_object_type(name="TaskMutationOutput", fields=fields)
