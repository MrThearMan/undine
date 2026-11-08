from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from undine import Entrypoint, Field, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLValidationError


class UserType(QueryType[User], auto=False):
    username = Field()
    email = Field()


class Mutation(RootType):
    @Entrypoint
    def login(self, info: GQLInfo, username: str, password: str) -> UserType:
        request = info.context.request
        user = authenticate(request, username=username, password=password)
        if user is None:
            msg = "Invalid username or password."
            raise GraphQLValidationError(msg)

        login(request, user)
        return user
