from undine import Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @name.convert
    def convert_name(self, value: str) -> str:
        return value.upper()
