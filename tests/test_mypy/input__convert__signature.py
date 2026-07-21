"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:15: error: Argument 1 to "convert" of "Input" has incompatible type "Callable[[TaskCreateMutation], str]"; expected "Callable[[Any, Any], Any] | None"  [arg-type]
main:16: error: The @bad.convert decorator must be applied to a method with signature 'def (self, value: Any) -> Any'  [misc]
"""

from example_project.app.models import Task
from undine import Input, MutationType


class TaskCreateMutation(MutationType[Task]):
    good = Input(str)

    @good.convert
    def good_convert(self, value: str) -> str:
        return value

    bad = Input(str)

    @bad.convert
    def bad_convert(self) -> str:
        return ""
