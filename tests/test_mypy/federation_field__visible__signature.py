"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:17: error: Argument 1 to "visible" of "FederationField" has incompatible type "Callable[[BookExtension], bool]"; expected "Callable[[Any, DjangoRequestProtocol[Any]], bool] | None"  [arg-type]
main:18: error: The @bad.visible decorator must be applied to a method with signature 'def (self, request: DjangoRequestProtocol) -> bool'  [misc]
"""

from undine.federation import FederationField, FederationType, KeyDirective
from undine.typing import DjangoRequestProtocol


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str)
    good = FederationField(str)

    @good.visible
    def good_visible(self, request: DjangoRequestProtocol) -> bool:
        return True

    bad = FederationField(str)

    @bad.visible
    def bad_visible(self) -> bool:
        return True
