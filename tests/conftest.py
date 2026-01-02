from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

import pytest

from pytest_undine.fixtures import graphql, graphql_async, undine_settings
from tests.factories._base import UndineFaker
from tests.helpers import SessionStore
from undine.query import QUERY_TYPE_REGISTRY
from undine.utils.graphql.type_registry import GRAPHQL_REGISTRY, register_builtins

if TYPE_CHECKING:
    from tests.helpers import AccessLog

__all__ = [
    "graphql",
    "graphql_async",
    "undine_settings",
]


@pytest.fixture(autouse=True)
def _clear_registries() -> None:
    QUERY_TYPE_REGISTRY.clear()
    GRAPHQL_REGISTRY.clear()

    register_builtins()


@pytest.fixture(autouse=True)
def _reset_faker_uniqueness() -> None:
    """Reset the uniqueness between tests so that we don't run out of unique values."""
    UndineFaker.clear_unique()


@pytest.fixture
def session_logger(settings) -> Generator[AccessLog, Any, None]:
    """Replaces current session with one that logs all reads and writes to the session."""
    settings.SESSION_ENGINE = "tests.helpers"
    SessionStore.log = []
    try:
        yield SessionStore.log
    finally:
        SessionStore.log = []
