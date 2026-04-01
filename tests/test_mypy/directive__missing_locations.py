"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:5: error: Missing required class definition keyword argument "locations" for "TestDirective"  [misc]
"""

from undine import Directive


class TestDirective(Directive): ...
