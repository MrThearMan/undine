import pytest
from graphql import GraphQLWrappingType

from undine.registies import GRAPHQL_TYPE_REGISTRY, QUERY_TYPE_REGISTRY


@pytest.fixture(autouse=True)
def _clear_registies() -> None:
    QUERY_TYPE_REGISTRY.clear()
    GRAPHQL_TYPE_REGISTRY.clear()


@pytest.fixture(autouse=True, scope="session")
def _patch_graphql_objects() -> None:
    # Set wrapping types to compare their wrapped types.
    def wrapping_eq(self: GraphQLWrappingType, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.of_type == other.of_type

    GraphQLWrappingType.__eq__ = wrapping_eq
