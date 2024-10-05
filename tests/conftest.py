import pytest

from undine.registry import TYPE_REGISTRY


@pytest.fixture(autouse=True)
def _clear_type_registry() -> None:
    TYPE_REGISTRY.clear()
