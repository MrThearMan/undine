"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:5: error: OrderSet must be parameterized with one or more Django Models  [misc]
"""

from undine.ordering import OrderSet


class TaskOrderSet(OrderSet): ...
