"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:12: error: Directive "TestDirective" does not support location "FIELD_DEFINITION"  [misc]
main:14: error: Directive "TestDirective" does not support location "FIELD_DEFINITION"  [misc]
main:19: error: Directive "TestDirective" does not support location "FIELD_DEFINITION"  [misc]
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Directive, Field, GQLInfo, QueryType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class TaskType(QueryType[Task]):
    name = Field() @ TestDirective()

    @TestDirective()
    @Field()
    def foo(self, info: GQLInfo) -> int:
        return 0

    @TestDirective()
    @Field
    async def bar(self, info: GQLInfo) -> int:
        return 0
