"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from django.db.models import Value

from example_project.app.models import Task
from undine import DjangoExpression, GQLInfo, Order, OrderSet
from undine.typing import DjangoRequestProtocol


class TaskOrderSet(OrderSet[Task]):
    name = Order()

    @name.aliases
    def name_aliases(self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]:
        assert_type(self, Order)
        return {"foo": Value("bar")}

    @name.visible
    def name_visible(self, request: DjangoRequestProtocol) -> bool:
        assert_type(self, Order)
        return True
