"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:20: error: Argument 1 to "aliases" of "Filter" has incompatible type "Callable[[TaskFilterSet, GQLInfo[Any]], dict[str, DjangoExpression]]"; expected "FilterAliasesFunc | None"  [arg-type]
main:21: error: The @bad.aliases decorator must be applied to a method with signature 'def (self, info: GQLInfo, *, value: Any) -> dict[str, DjangoExpression]'  [misc]
"""

from django.db.models import Q, Value

from example_project.app.models import Task
from undine import Filter, FilterSet, GQLInfo
from undine.typing import DjangoExpression


class TaskFilterSet(FilterSet[Task]):
    good = Filter()

    @good.aliases
    def good_aliases(self, info: GQLInfo, *, value: str) -> dict[str, DjangoExpression]:
        return {"foo": Value("bar")}

    @Filter
    def bad(self, info: GQLInfo, *, value: str) -> Q:
        return Q()

    @bad.aliases
    def bad_aliases(self, info: GQLInfo) -> dict[str, DjangoExpression]:
        return {"foo": Value("bar")}
