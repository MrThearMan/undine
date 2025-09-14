from undine import Input, MutationType
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
