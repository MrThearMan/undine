from __future__ import annotations

import pytest
from graphql import GraphQLWrappingType

from pytest_undine.fixtures import graphql, undine_settings
from tests.factories._base import UndineFaker
from undine.query import QUERY_TYPE_REGISTRY
from undine.utils.graphql.type_registry import GRAPHQL_REGISTRY, register_builtins

__all__ = [
    "graphql",
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


@pytest.fixture(autouse=True, scope="session")
def _patch_graphql_objects() -> None:
    # Set wrapping types to compare their wrapped types.
    def wrapping_eq(self: GraphQLWrappingType, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.of_type == other.of_type

    GraphQLWrappingType.__eq__ = wrapping_eq  # type: ignore[method-assign,assignment]
