"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import Any

from graphql import DirectiveLocation

from undine import Directive, DirectiveArgument


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]):
    one = DirectiveArgument(str)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


TestDirective(1, 2, foo="bar")
