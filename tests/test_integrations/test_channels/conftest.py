from __future__ import annotations

import pytest
from django.conf import settings as django_settings
from django.core.cache import caches


@pytest.fixture(autouse=True)
def _clear_sse_cache():
    """Handle clearing the session cache between runs so that cache data is not shared between tests."""
    cache = caches[django_settings.SESSION_CACHE_ALIAS]
    cache.clear()
    try:
        yield
    finally:
        cache.clear()
