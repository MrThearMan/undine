"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from example_project.app.models import Task
from undine import GQLInfo
from undine.optimizer import OptimizationData
from undine.query import Field, QueryType
from undine.typing import DjangoRequestProtocol


class TaskType(QueryType[Task]):
    @Field
    def foo(self) -> str:
        assert_type(self, Task)
        return "foo"

    bar = Field()

    @bar.resolve
    def resolve_bar(self) -> str:
        assert_type(self, Task)
        return "bar"

    @bar.optimize
    def optimize_bar(self, data: OptimizationData, info: GQLInfo) -> None:
        assert_type(self, Field)

    @bar.permissions
    def bar_permissions(self, info: GQLInfo, value: str) -> None:
        assert_type(self, Task)

    @bar.visible
    def bar_visible(self, request: DjangoRequestProtocol) -> bool:
        assert_type(self, Field)
        return True
