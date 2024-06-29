from __future__ import annotations

from types import ModuleType

from django.apps import AppConfig


class UndineConfig(AppConfig):
    name = "undine"
    label = "undine"
    verbose_name = "Undine"

    def ready(self) -> None:
        # Converter-modules can define a `load_deferred_converters` function,
        # which is used to delay registration of some converters until
        # django apps are ready. This is to avoid circular imports and
        # issues importing from other django apps.
        import undine.converters
        from undine.utils import get_members

        for _, module in get_members(undine.converters, ModuleType):
            if hasattr(module, "load_deferred_converters") and callable(module.load_deferred_converters):
                module.load_deferred_converters()
