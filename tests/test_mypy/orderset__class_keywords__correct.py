"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine.directives import Directive
from undine.ordering import OrderSet


class MockDirective(Directive, locations=[DirectiveLocation.ENUM]): ...


class TaskOrderSet(
    OrderSet[Task],
    auto=True,
    exclude=["foo", "bar"],
    schema_name="TaskOrder",
    directives=[MockDirective()],
    extensions={"foo": "bar"},
): ...
