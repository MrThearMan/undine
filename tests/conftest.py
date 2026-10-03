from __future__ import annotations

import gc
import os
from typing import TYPE_CHECKING, Any, Callable, Generator

import pytest
from django.urls import resolve

from pytest_undine.fixtures import graphql, graphql_async, undine_settings
from tests.factories._base import UndineFaker
from tests.helpers import SessionStore
from undine.directives import AtomicDirective, CacheRulesDirective, ComplexityDirective
from undine.federation.directives import USED_FEDERATION_DIRECTIVES
from undine.federation.federation_type import FEDERATION_TYPE_REGISTRY
from undine.hooks import ParseCacheHook, ValidationCacheHook, get_enabled_lifecycle_hooks
from undine.query import QUERY_TYPE_REGISTRY
from undine.relay import Node
from undine.utils.graphql.type_registry import DIRECTIVE_REGISTRY, GRAPHQL_REGISTRY, register_builtins
from undine.utils.reflection import get_signature

if TYPE_CHECKING:
    from tests.helpers import AccessLog

__all__ = [
    "graphql",
    "graphql_async",
    "undine_settings",
]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--gc-after-each-test",
        action="store_true",
        default=False,
        help=(
            "Run garbage collection after each test, so that warnings raised during garbage collection "
            "(e.g. 'ResourceWarning') are reported on the test that caused them. Slows the suite down a lot."
        ),
    )


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    if item.config.getoption("--gc-after-each-test"):
        gc.collect()


@pytest.fixture(scope="session", autouse=True)
def _load_url_conf() -> None:
    """
    Django imports the URL conf lazily on the first request, and `undine.http.urls` reads
    `GRAPHQL_PATH` and `ASYNC` at import time. Load it before any test can change those settings,
    so that the first test making a request doesn't decide the GraphQL view for the whole session.
    """
    resolve("/graphql/")


@pytest.fixture(autouse=True)
def _clear_registries() -> None:
    QUERY_TYPE_REGISTRY.clear()
    GRAPHQL_REGISTRY.clear()
    DIRECTIVE_REGISTRY.clear()
    USED_FEDERATION_DIRECTIVES.clear()
    FEDERATION_TYPE_REGISTRY.clear()

    ParseCacheHook.cache.clear()
    ValidationCacheHook.cache.clear()

    get_enabled_lifecycle_hooks.cache_clear()

    Node.__implementations__.clear()

    get_signature.cache.clear()

    DIRECTIVE_REGISTRY[AtomicDirective.__schema_name__] = AtomicDirective
    DIRECTIVE_REGISTRY[CacheRulesDirective.__schema_name__] = CacheRulesDirective
    DIRECTIVE_REGISTRY[ComplexityDirective.__schema_name__] = ComplexityDirective

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


def skip_if_async(func: Callable[..., Any]) -> Any:
    return pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Sync only")(func)
