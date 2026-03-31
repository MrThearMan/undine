"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from example_project.app.models import Task
from undine.mutation import Input, MutationType
from undine.typing import DjangoRequestProtocol, GQLInfo


class TaskCreateMutation(MutationType[Task]):
    @Input
    def foo(self, info: GQLInfo) -> str:
        assert_type(self, Task)
        return "foo"

    bar = Input(str)

    @bar.validate
    def validate_bar(self, info: GQLInfo, value: str) -> None:
        assert_type(self, Task)

    @bar.permissions
    def bar_permissions(self, info: GQLInfo, value: str) -> None:
        assert_type(self, Task)

    @bar.convert
    def bar_convert(self, value: str) -> str:
        assert_type(self, Input)
        return value

    @bar.visible
    def bar_visible(self, request: DjangoRequestProtocol) -> bool:
        assert_type(self, Input)
        return True
