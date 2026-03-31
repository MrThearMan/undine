"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:14: error: The second argument to "bar" must be named "info"  [misc]
main:24: error: The second argument to "bax" must be named "info"  [misc]
"""

from example_project.app.models import Task
from undine import Input, MutationType
from undine.typing import GQLInfo


class TaskCreateMutation(MutationType[Task]):
    @Input
    def foo(self, info: GQLInfo, value: str) -> str:
        """Correct signature: function input"""
        return value.upper()

    @Input
    def bar(self, value: str) -> str:
        """Incorrect signature: missing info"""
        return value.upper()

    @Input
    def baz(self, info: GQLInfo) -> str:
        """Correct signature: hidden field"""
        return "baz"

    @Input
    def bax(self, value: str, info: GQLInfo) -> str:
        """Incorrect signature: info should be second parameter"""
        return value.upper()
