import random

from graphql import GraphQLError

from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    @Field(errors=[GraphQLError])
    def example(self) -> str:
        if random.random() > 0.5:
            msg = "Failed"
            raise GraphQLError(msg)
        return "OK"
