from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from django.apps import AppConfig

if TYPE_CHECKING:
    from types import ModuleType


class UndineConfig(AppConfig):
    name = "undine"
    label = "undine"
    verbose_name = "undine"

    def ready(self) -> None:
        import undine.converters  # noqa: PLC0415
        import undine.parsers  # noqa: PLC0415

        self.load_deferred(module=undine.converters)
        self.load_deferred(module=undine.parsers)

    def load_deferred(self, module: ModuleType) -> None:
        """
        If any submodule in the given module defines a `load_deferred` function,
        run that function without any arguments.

        This can be used to delay running some code until django apps are ready.
        This is to avoid circular imports and issues importing models from other django apps.
        """
        from undine.utils.reflection import has_callable_attribute  # noqa: PLC0415

        converter_dir = Path(module.__file__).resolve().parent
        lib_root = converter_dir.parent.parent

        for file in converter_dir.glob("**/*.py"):
            import_path = file.relative_to(lib_root).as_posix().replace("/", ".").removesuffix(".py")
            module = import_module(import_path)

            if has_callable_attribute(module, "load_deferred"):
                module.load_deferred()
