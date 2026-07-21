"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:14: error: Argument 1 to "permissions" of "Field" has incompatible type "Callable[[TaskType], None]"; expected "Callable[[Any, GQLInfo[Any], Any], Awaitable[None] | None] | None"  [arg-type]
main:15: error: The @bad.permissions decorator must be applied to a method with signature 'def (self, info: GQLInfo, value: Any) -> None'  [misc]
"""

from example_project.app.models import Task
from undine import Field, GQLInfo, QueryType


class TaskType(QueryType[Task]):
    good = Field()

    @good.permissions
    def good_permissions(self, info: GQLInfo, value: str) -> None: ...

    bad = Field()

    @bad.permissions
    def bad_permissions(self) -> None: ...
