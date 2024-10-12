import pytest

from undine.registies import QUERY_TYPE_REGISTRY


@pytest.fixture(autouse=True)
def _clear_registies() -> None:
    QUERY_TYPE_REGISTRY.clear()
