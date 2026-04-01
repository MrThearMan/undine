"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Directive, Field, GQLInfo, QueryType


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class TaskType(QueryType[Task]):
    name = Field() @ TestDirective()

    @TestDirective()
    @Field
    def foo(self, info: GQLInfo) -> int:
        return 0

    @TestDirective()
    @Field
    async def bar(self, info: GQLInfo) -> int:
        return 0
