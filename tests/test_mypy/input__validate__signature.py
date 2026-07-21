"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:14: error: Argument 1 to "validate" of "Input" has incompatible type "Callable[[TaskCreateMutation], None]"; expected "Callable[[Any, GQLInfo[Any], Any], Awaitable[None] | None] | None"  [arg-type]
main:15: error: The @bad.validate decorator must be applied to a method with signature 'def (self, info: GQLInfo, value: Any) -> None'  [misc]
"""

from example_project.app.models import Task
from undine import GQLInfo, Input, MutationType


class TaskCreateMutation(MutationType[Task]):
    good = Input(str)

    @good.validate
    def good_validate(self, info: GQLInfo, value: str) -> None: ...

    bad = Input(str)

    @bad.validate
    def bad_validate(self) -> None: ...
