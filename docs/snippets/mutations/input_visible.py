from undine import Input, MutationType
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @name.visible
    def name_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
