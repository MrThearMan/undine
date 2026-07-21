"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:12: error: Return type of resolver for "title" is incompatible with the Field ref type; expected a subtype of the ref type  [misc]
main:15: error: Return type of resolver for "tags" is incompatible with the Field ref type; expected a subtype of the ref type  [misc]
"""

from example_project.app.models import Task
from undine import Field, GQLInfo, QueryType


class TaskType(QueryType[Task]):
    title = Field(str)
    tags = Field(str, many=True)
    subtitle = Field(str, nullable=True)

    @title.resolve
    def resolve_title(self, info: GQLInfo) -> int: ...

    @tags.resolve
    def resolve_tags(self, info: GQLInfo) -> str: ...

    @subtitle.resolve
    def resolve_subtitle(self, info: GQLInfo) -> str: ...
