"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:8: error: Argument "info" has incompatible type "str"; expected 'undine.typing.GQLInfo'  [arg-type]
main:14: error: Argument "info" has incompatible type "str"; expected 'undine.typing.GQLInfo'  [arg-type]
"""

from example_project.app.models import Task
from undine import Field, QueryType


class TaskType(QueryType[Task]):
    @Field
    def foo(self, info: str) -> str:
        return "foo"

    bar = Field()

    @bar.resolve
    def resolve_bar(self, info: str) -> str:
        return "bar"
