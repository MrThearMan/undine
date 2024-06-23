import inspect

from django.apps import AppConfig


class UndineConfig(AppConfig):
    name = "undine"

    def ready(self) -> None:
        # Converter-modules can define a `load_deferred_converters` function,
        # which is used to delay registration of some converters until
        # django apps are ready. This is to avoid circular imports and
        # issues importing from other django apps.
        import undine.converters

        for _, module in inspect.getmembers(undine.converters, inspect.ismodule):
            if hasattr(module, "load_deferred_converters") and callable(module.load_deferred_converters):
                module.load_deferred_converters()
