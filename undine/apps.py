from __future__ import annotations

from importlib import import_module
from pathlib import Path

from django.apps import AppConfig


class UndineConfig(AppConfig):
    name = "undine"
    label = "undine"
    verbose_name = "undine"

    def ready(self) -> None:
        self.load_deferred_converters()

    def load_deferred_converters(self) -> None:
        """
        Modules in `undine.converters` can define a `load_deferred_converters` function,
        which is used to delay registration of some converters until
        django apps are ready. This is to avoid circular imports and
        issues importing models from other django apps.
        """
        import undine.converters  # noqa: PLC0415
        from undine.utils.reflection import has_callable_attribute  # noqa: PLC0415

        converter_dir = Path(undine.converters.__file__).resolve().parent
        lib_root = converter_dir.parent.parent

        for file in converter_dir.glob("**/*.py"):
            import_path = file.relative_to(lib_root).as_posix().replace("/", ".").removesuffix(".py")
            module = import_module(import_path)

            if has_callable_attribute(module, "load_deferred_converters"):
                module.load_deferred_converters()
