from django.contrib.auth.models import User

from undine import Entrypoint, Field, GQLInfo, QueryType, RootType


class UserType(QueryType[User], auto=False):
    username = Field()
    email = Field()


class Query(RootType):
    @Entrypoint
    def me(self, info: GQLInfo) -> UserType | None:
        user = info.context.request.user
        if not user.is_authenticated:
            return None
        return user
