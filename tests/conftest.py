from __future__ import annotations

import pytest

from pytest_undine.fixtures import graphql, graphql_async, undine_settings
from tests.factories._base import UndineFaker
from undine.query import QUERY_TYPE_REGISTRY
from undine.utils.graphql.type_registry import GRAPHQL_REGISTRY, register_builtins

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
