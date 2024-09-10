"""Module for loading Undine as a Django app."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

from django.apps import AppConfig


class UndineConfig(AppConfig):
    name = "undine"
    label = "undine"
    verbose_name = "undine"

    def ready(self) -> None:
        import undine.converters

        self.load_deferred(undine.converters)

    def load_deferred(self, module: ModuleType) -> None:
        """
        Converter-modules can define a `load_deferred_converters` function,
        which is used to delay registration of some converters until
        django apps are ready. This is to avoid circular imports and
        issues importing models from other django apps.
        """
        from undine.utils.reflection import get_members, has_callable_attribute

        root_path = Path(module.__file__).parent

        for _, submodule in get_members(module, ModuleType):
            if has_callable_attribute(submodule, "load_deferred_converters"):
                submodule.load_deferred_converters()
            # Also load from sub-modules inside `undine.converters`
            if Path(submodule.__file__).parent.is_relative_to(root_path):
                self.load_deferred(submodule)
