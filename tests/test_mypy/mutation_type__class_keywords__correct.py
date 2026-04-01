"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Directive, MutationType


class MockDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT]): ...


class TaskCreateMutation(
    MutationType[Task],
    kind="create",
    related_action="null",
    auto=True,
    exclude=["foo", "bar"],
    schema_name="TaskMutation",
    directives=[MockDirective()],
    extensions={"foo": "bar"},
): ...
