from __future__ import annotations

from pathlib import Path
from types import ModuleType

from django.apps import AppConfig


class UndineConfig(AppConfig):
    name = "undine"
    label = "undine"
    verbose_name = "Undine"

    def ready(self) -> None:
        import undine.converters

        self.load_deferred(undine.converters)

    def load_deferred(self, module: ModuleType) -> None:
        """
        Converter-modules can define a `load_deferred_converters` function,
        which is used to delay registration of some converters until
        django apps are ready. This is to avoid circular imports and
        issues importing from other django apps.
        """
        from undine.utils.reflection import get_members

        root_path = Path(module.__file__).parent

        for _, submodule in get_members(module, ModuleType):
            if hasattr(submodule, "load_deferred_converters") and callable(submodule.load_deferred_converters):
                submodule.load_deferred_converters()
            # Also load from sub-modules of the module
            if Path(submodule.__file__).parent.is_relative_to(root_path):
                self.load_deferred(submodule)
