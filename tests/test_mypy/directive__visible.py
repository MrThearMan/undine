"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:15: error: Argument 1 to "visible" of "DirectiveArgument" has incompatible type "Callable[[TestDirective], bool]"; expected "Callable[[Any, DjangoRequestProtocol[Any]], bool] | None"  [arg-type]
main:16: error: The @name.visible decorator must be applied to a method with signature 'def (self, request: DjangoRequestProtocol) -> bool'  [misc]
"""

from graphql import DirectiveLocation

from undine import Directive, DirectiveArgument
from undine.typing import DjangoRequestProtocol


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]):
    name = DirectiveArgument(str)

    @name.visible
    def name_visible(self, request: DjangoRequestProtocol) -> bool:
        return True

    @name.visible
    def name_visible_bad(self) -> bool:
        return True
