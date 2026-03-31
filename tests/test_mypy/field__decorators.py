"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from example_project.app.models import Task
from undine import Field
from undine.query import QueryType
from undine.typing import GQLInfo


class TaskType(QueryType[Task]):
    @Field
    def a(self, info: GQLInfo) -> int:
        """Regular method field"""
        return 0

    @Field
    def b(self) -> int:
        """Regular method field without info"""
        return 0

    @Field
    def c(self, info: GQLInfo, arg: int) -> int:
        """Regular method field with argument"""
        return 0

    @Field
    def d(self, arg: int) -> int:
        """Regular method field with argument and without info"""
        return 0

    @Field
    async def e(self, info: GQLInfo) -> int:
        """Async method field"""
        return 0

    @Field
    async def f(self) -> int:
        """Async method field without info"""
        return 0

    @Field
    async def g(self, info: GQLInfo, arg: int) -> int:
        """Async method field with argument"""
        return 0

    @Field
    async def h(self, arg: int) -> int:
        """Async method field with argument and without info"""
        return 0
