from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

from django.apps import apps
from graphql.pyutils import did_you_mean

if TYPE_CHECKING:
    from undine.apps import UndineConfig


def get_undine_config() -> UndineConfig:
    return apps.get_app_config("undine")  # type: ignore[return-value]


def test_apps__patch_introspection_types__experimental_visibility_enabled(undine_settings) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    config = get_undine_config()

    path = "undine.utils.graphql.introspection.patch_introspection_schema"
    with patch(path) as mock_patch:
        config.patch_introspection_types()

    mock_patch.assert_called_once()


def test_apps__patch_introspection_types__experimental_visibility_disabled(undine_settings) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = False

    config = get_undine_config()

    path = "undine.utils.graphql.introspection.patch_introspection_schema"
    with patch(path) as mock_patch:
        config.patch_introspection_types()

    mock_patch.assert_not_called()


def test_apps__maybe_disable_did_you_mean__disabled(undine_settings) -> None:
    undine_settings.ALLOW_DID_YOU_MEAN_SUGGESTIONS = False

    config = get_undine_config()
    config.maybe_disable_did_you_mean()

    assert did_you_mean.__globals__["MAX_LENGTH"] == 0


def test_apps__patch_debug_toolbar_if_installed__debug_toolbar_installed() -> None:
    config = get_undine_config()

    path = "undine.integrations.debug_toolbar.monkeypatch_middleware"
    with patch(path) as mock_patch:
        config.patch_debug_toolbar_if_installed()

    mock_patch.assert_called_once()


def test_apps__patch_debug_toolbar_if_installed__import_error() -> None:
    config = get_undine_config()

    saved_module = sys.modules.pop("undine.integrations.debug_toolbar", None)
    try:
        sys.modules["undine.integrations.debug_toolbar"] = None  # type: ignore[assignment]
        config.patch_debug_toolbar_if_installed()
    finally:
        if saved_module is not None:
            sys.modules["undine.integrations.debug_toolbar"] = saved_module
        else:
            sys.modules.pop("undine.integrations.debug_toolbar", None)


def test_apps__patch_debug_toolbar_if_installed__runtime_error() -> None:
    config = get_undine_config()

    class _RaisesRuntimeError:
        def __getattr__(self, name: str) -> None:
            msg = "debug toolbar not in INSTALLED_APPS"
            raise RuntimeError(msg)

    saved_module = sys.modules.pop("undine.integrations.debug_toolbar", None)
    try:
        sys.modules["undine.integrations.debug_toolbar"] = _RaisesRuntimeError()  # type: ignore[assignment]
        config.patch_debug_toolbar_if_installed()
    finally:
        if saved_module is not None:
            sys.modules["undine.integrations.debug_toolbar"] = saved_module
        else:
            sys.modules.pop("undine.integrations.debug_toolbar", None)
