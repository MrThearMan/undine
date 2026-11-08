from django.contrib.auth import logout

from undine import Entrypoint, GQLInfo, RootType


class Mutation(RootType):
    @Entrypoint
    def logout(self, info: GQLInfo) -> bool:
        logout(info.context.request)
        return True
