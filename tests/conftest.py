import pytest

from undine.registies import GRAPHQL_ENUM_REGISTRY, QUERY_TYPE_REGISTRY


@pytest.fixture(autouse=True)
def _clear_registies() -> None:
    QUERY_TYPE_REGISTRY.clear()
    GRAPHQL_ENUM_REGISTRY.clear()
