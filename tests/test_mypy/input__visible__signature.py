"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:16: error: Argument 1 to "visible" of "Input" has incompatible type "Callable[[TaskCreateMutation], bool]"; expected "Callable[[Any, DjangoRequestProtocol[Any]], bool] | None"  [arg-type]
main:17: error: The @bad.visible decorator must be applied to a method with signature 'def (self, request: DjangoRequestProtocol) -> bool'  [misc]
"""

from example_project.app.models import Task
from undine import Input, MutationType
from undine.typing import DjangoRequestProtocol


class TaskCreateMutation(MutationType[Task]):
    good = Input(str)

    @good.visible
    def good_visible(self, request: DjangoRequestProtocol) -> bool:
        return True

    bad = Input(str)

    @bad.visible
    def bad_visible(self) -> bool:
        return True
