"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:5: error: MutationType must be parameterized with a single Django Model  [misc]
"""

from undine.mutation import MutationType


class TaskCreateMutation(MutationType): ...
