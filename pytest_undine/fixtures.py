from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from settings_holder import SettingsHolder

    from undine.testing import GraphQLClient

__all__ = [
    "graphql",
    "undine_settings",
]


@pytest.fixture
def graphql() -> GraphQLClient:
    from undine.testing import GraphQLClient  # noqa: PLC0415

    return GraphQLClient()


@pytest.fixture
def undine_settings() -> SettingsHolder:
    from undine import settings  # noqa: PLC0415

    try:
        yield settings.undine_settings
    finally:
        for attribute in settings.undine_settings.__dict__:
            if attribute.isupper():
                settings.undine_settings._cached_attrs.add(attribute)  # noqa: SLF001
        settings.undine_settings.reload()
