from undine import GQLInfo, Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    @Input
    def name(self, info: GQLInfo, value: str) -> str:
        return value.upper()
