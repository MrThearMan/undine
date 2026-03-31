"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:8: error: Argument "info" has incompatible type "str"; expected 'undine.typing.GQLInfo'  [arg-type]
"""

from example_project.app.models import Task
from undine import Input, MutationType


class TaskCreateMutation(MutationType[Task]):
    @Input
    def name(self, info: str, value: str) -> str:
        return value.upper()
