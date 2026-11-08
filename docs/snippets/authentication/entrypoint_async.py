from django.contrib.auth import aauthenticate, alogin, alogout
from django.contrib.auth.models import User

from undine import Entrypoint, Field, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLValidationError


class UserType(QueryType[User], auto=False):
    username = Field()
    email = Field()


class Query(RootType):
    @Entrypoint
    async def me(self, info: GQLInfo) -> UserType | None:
        user = await info.context.request.auser()
        if not user.is_authenticated:
            return None
        return user


class Mutation(RootType):
    @Entrypoint
    async def login(self, info: GQLInfo, username: str, password: str) -> UserType:
        request = info.context.request
        user = await aauthenticate(request, username=username, password=password)
        if user is None:
            msg = "Invalid username or password."
            raise GraphQLValidationError(msg)

        await alogin(request, user)
        return user

    @Entrypoint
    async def logout(self, info: GQLInfo) -> bool:
        await alogout(info.context.request)
        return True
