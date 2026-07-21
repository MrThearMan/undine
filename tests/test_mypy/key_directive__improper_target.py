"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:5: error: Class "A" does not support directives  [misc]
"""

from undine.federation import KeyDirective


@KeyDirective(fields="id")
class A: ...
