"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:22: error: Argument 1 to "aliases" of "Order" has incompatible type "Callable[[TaskOrderSet, GQLInfo[Any]], dict[str, DjangoExpression]]"; expected "OrderAliasesFunc | None"  [arg-type]
main:23: error: The @done.aliases decorator must be applied to a method with signature 'def (self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]'  [misc]
main:26: error: Argument 1 to "visible" of "Order" has incompatible type "Callable[[TaskOrderSet], bool]"; expected "Callable[[Any, DjangoRequestProtocol[Any]], bool] | None"  [arg-type]
main:27: error: The @done.visible decorator must be applied to a method with signature 'def (self, request: DjangoRequestProtocol) -> bool'  [misc]
"""

from django.db.models import Value

from example_project.app.models import Task
from undine import GQLInfo, Order, OrderSet
from undine.typing import DjangoExpression, DjangoRequestProtocol


class TaskOrderSet(OrderSet[Task]):
    name = Order()

    @name.aliases
    def name_aliases(self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]:
        return {"foo": Value("bar")}

    @name.visible
    def name_visible(self, request: DjangoRequestProtocol) -> bool:
        return True

    done = Order()

    @done.aliases
    def done_aliases(self, info: GQLInfo) -> dict[str, DjangoExpression]:
        return {"foo": Value("bar")}

    @done.visible
    def done_visible(self) -> bool:
        return True
