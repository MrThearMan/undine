from undine import GQLInfo, Input, MutationType
from undine.exceptions import GraphQLValidationError

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @name.validate
    def validate_name(self, info: GQLInfo, value: str) -> None:
        if len(value) < 3:
            msg = "Name must be at least 3 characters."
            raise GraphQLValidationError(msg)
