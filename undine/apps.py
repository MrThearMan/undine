from __future__ import annotations

from importlib import import_module
from pathlib import Path

from django.apps import AppConfig


class UndineConfig(AppConfig):
    name = "undine"
    label = "undine"
    verbose_name = "undine"

    def ready(self) -> None:
        self.register_additional_types()
        self.register_converters()
        self.maybe_disable_did_you_mean()
        self.patch_debug_toolbar_if_installed()

    def register_additional_types(self) -> None:
        from undine.utils.graphql.type_registry import register_builtins  # noqa: PLC0415

        register_builtins()

    def register_converters(self) -> None:
        """Import all converter implementation modules to register the implementations to the converters."""
        import undine.converters  # noqa: PLC0415

        converter_dir = Path(undine.converters.__file__).resolve().parent
        lib_root = converter_dir.parent.parent

        for file in converter_dir.glob("impl/*.py"):
            import_path = file.relative_to(lib_root).as_posix().replace("/", ".").removesuffix(".py")
            import_module(import_path)

    def maybe_disable_did_you_mean(self) -> None:
        """Disable the 'did you mean' suggestions on error messages if `DISABLE_DID_YOU_MEAN` is True."""
        from graphql.pyutils import did_you_mean  # noqa: PLC0415

        from undine.settings import undine_settings  # noqa: PLC0415

        # See: https://github.com/graphql-python/graphql-core/issues/97#issuecomment-642967670
        if not undine_settings.ALLOW_DID_YOU_MEAN_SUGGESTIONS:
            did_you_mean.__globals__["MAX_LENGTH"] = 0

    def patch_debug_toolbar_if_installed(self) -> None:
        """Patch `django-debug-toolbar` to work with Undine if it's installed."""
        try:
            from undine.integrations.debug_toolbar import monkeypatch_middleware  # noqa: PLC0415
        except ImportError:
            return

        monkeypatch_middleware()
