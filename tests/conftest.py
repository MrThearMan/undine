import pytest

from undine.registry import REGISTRY


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    REGISTRY.clear()
