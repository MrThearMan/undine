from undine import GQLInfo, Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    @Input
    def current_user(self, info: GQLInfo) -> int | None:
        return info.context.user.id
