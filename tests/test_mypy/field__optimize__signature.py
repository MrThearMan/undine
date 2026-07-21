"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:15: error: Argument 1 to "optimize" of "Field" has incompatible type "Callable[[TaskType], None]"; expected "Callable[[Any, OptimizationData, GQLInfo[Any]], None] | None"  [arg-type]
main:16: error: The @bad.optimize decorator must be applied to a method with signature 'def (self, info: GQLInfo) -> None'  [misc]
"""

from example_project.app.models import Task
from undine import Field, GQLInfo, QueryType
from undine.optimizer import OptimizationData


class TaskType(QueryType[Task]):
    good = Field()

    @good.optimize
    def good_optimize(self, data: OptimizationData, info: GQLInfo) -> None: ...

    bad = Field()

    @bad.optimize
    def bad_optimize(self) -> None: ...
