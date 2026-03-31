"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:5: error: QueryType must be parameterized with a single Django Model  [misc]
"""

from undine.query import QueryType


class TaskType(QueryType): ...
