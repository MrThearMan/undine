import random

from graphql import GraphQLError

from undine import Entrypoint, RootType


class Query(RootType):
    @Entrypoint(errors=[GraphQLError])
    def example(self) -> str:
        if random.random() > 0.5:
            msg = "Failed"
            raise GraphQLError(msg)
        return "OK"
