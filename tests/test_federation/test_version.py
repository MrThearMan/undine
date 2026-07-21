from __future__ import annotations

import pytest

from example_project.app.models import Task
from undine import Entrypoint, Field, QueryType, RootType
from undine.directives import Directive
from undine.exceptions import UnsupportedFederationVersionError
from undine.federation import create_federation_schema
from undine.federation import directives as fed_directives_module
from undine.federation.version import (
    SUPPORTED_FEDERATION_VERSIONS,
    is_supported_federation_version,
    is_supported_in_federation_version,
    parse_version,
)
from undine.settings import undine_settings


def test_parse_version() -> None:
    assert parse_version("2.0") == (2, 0)
    assert parse_version("2.11") == (2, 11)
    assert parse_version("2.11") > parse_version("2.5")


def test_is_supported_federation_version() -> None:
    for version in SUPPORTED_FEDERATION_VERSIONS:
        assert is_supported_federation_version(version)
    assert not is_supported_federation_version("1.0")
    assert not is_supported_federation_version("2.16")
    assert not is_supported_federation_version("3.0")
    assert not is_supported_federation_version("nope")


def test_is_supported_in_federation_version(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.14"
    assert is_supported_in_federation_version("2.14")
    assert is_supported_in_federation_version("2.0")
    assert not is_supported_in_federation_version("2.15")


def test_create_federation_schema__valid_version(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.15"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    create_federation_schema(query=Query)


def test_create_federation_schema__unknown_version(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.99"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    with pytest.raises(UnsupportedFederationVersionError):
        create_federation_schema(query=Query)


def test_create_federation_schema__non_numeric_version(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "latest"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    with pytest.raises(UnsupportedFederationVersionError):
        create_federation_schema(query=Query)


def test_create_federation_schema__three_part_version(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.1.1"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    with pytest.raises(UnsupportedFederationVersionError):
        create_federation_schema(query=Query)


@pytest.mark.parametrize("version", SUPPORTED_FEDERATION_VERSIONS)
def test_create_federation_schema__every_supported_version(undine_settings, version) -> None:
    undine_settings.FEDERATION_VERSION = version

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    create_federation_schema(query=Query)


# Stale-version-workaround maintenance guard


def _collect_min_version_workarounds() -> list[tuple[str, str]]:
    """
    Return `(location, threshold_version)` for every federation directive class that carries a
    `FEDERATION_MIN_VERSION_EXTENSIONS_KEY` entry in its extensions. Auto-picks up any new class
    in `undine.federation.directives`.
    """
    key = undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY
    workarounds: list[tuple[str, str]] = []
    for name in dir(fed_directives_module):
        cls = getattr(fed_directives_module, name)
        if not isinstance(cls, type) or cls is Directive or not issubclass(cls, Directive):
            continue
        extensions = cls.__dict__.get("__extensions__") or {}
        min_version = extensions.get(key)
        if min_version is None:
            continue
        workarounds.append((f"{cls.__module__}.{cls.__qualname__} extensions[{key!r}]", min_version))
    return workarounds


# Ad-hoc branches that don't live on a `min_version` class var and can't be discovered by scan.
# Keep in sync with the code — add an entry whenever calling `not is_supported_in_federation_version(...)`.
_AD_HOC_VERSION_WORKAROUNDS: list[tuple[str, str]] = [
    (
        "undine.federation.directives._ShareableIsRepeatable (@shareable pre-2.2 non-repeatable)",
        "2.2",
    ),
    (
        "undine.federation.directives.KeyDirective.__connected__ (@key on interface pre-2.3 gate)",
        "2.3",
    ),
    (
        "undine.federation.schema.create_federation_schema (subscription pre-2.4 gate)",
        "2.4",
    ),
    (
        "undine.federation.directives.OverrideDirective.__init__ (label pre-2.7 gate)",
        "2.7",
    ),
]


def test_no_stale_version_workarounds() -> None:
    """
    Fails when any version-conditional workaround exists for a version below the minimum
    supported version. The failure message lists every workaround that can now be deleted.
    """
    min_supported = min(parse_version(v) for v in SUPPORTED_FEDERATION_VERSIONS)

    stale: list[str] = []
    for location, threshold in _collect_min_version_workarounds() + _AD_HOC_VERSION_WORKAROUNDS:
        if parse_version(threshold) < min_supported:
            msg = f"  - {location}: threshold {threshold!r} <= min supported {'.'.join(map(str, min_supported))!r}"
            stale.append(msg)

    assert not stale, (
        "The following version-conditional workarounds are dead code because no supported "
        "Federation version needs them any more; delete them:\n" + "\n".join(stale)
    )
