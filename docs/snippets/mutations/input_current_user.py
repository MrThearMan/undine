from django.contrib.auth.models import User

from undine import GQLInfo, Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    @Input
    def user(self, info: GQLInfo) -> User | None:
        if info.context.user.is_anonymous:
            return None
        return info.context.user
