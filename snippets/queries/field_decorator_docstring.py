from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    @Field
    def testing(self, name: str) -> str:
        """
        Return a greeting.

        :param name: The name to greet.
        """
        return f"Hello, {name}!"
