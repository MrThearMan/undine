import pytest

from undine.registry import QUERY_TYPE_REGISTRY


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    QUERY_TYPE_REGISTRY.clear()
