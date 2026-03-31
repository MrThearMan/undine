"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:5: error: UnionType must be parameterized with at least two QueryTypes  [misc]
"""

from undine import UnionType


class NamedUnion(UnionType): ...
