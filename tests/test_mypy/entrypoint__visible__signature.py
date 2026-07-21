"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:15: error: Argument 1 to "visible" of "Entrypoint" has incompatible type "Callable[[Query], bool]"; expected "Callable[[Any, DjangoRequestProtocol[Any]], bool] | None"  [arg-type]
main:16: error: The @bad.visible decorator must be applied to a method with signature 'def (self, request: DjangoRequestProtocol) -> bool'  [misc]
"""

from undine import Entrypoint, RootType
from undine.typing import DjangoRequestProtocol


class Query(RootType):
    good = Entrypoint(str)

    @good.visible
    def good_visible(self, request: DjangoRequestProtocol) -> bool:
        return True

    bad = Entrypoint(str)

    @bad.visible
    def bad_visible(self) -> bool:
        return True
