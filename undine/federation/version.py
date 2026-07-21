from __future__ import annotations

from undine.settings import undine_settings

__all__ = [
    "SUPPORTED_FEDERATION_VERSIONS",
    "get_federation_spec_url",
    "is_supported_federation_version",
    "is_supported_in_federation_version",
    "parse_version",
]


SUPPORTED_FEDERATION_VERSIONS: tuple[str, ...] = (
    "2.0",
    "2.1",
    "2.2",
    "2.3",
    "2.4",
    "2.5",
    "2.6",
    "2.7",
    "2.8",
    "2.9",
    "2.10",
    "2.11",
    "2.12",
    "2.13",
    "2.14",
    "2.15",
)


def is_supported_federation_version(version: str) -> bool:
    return version in SUPPORTED_FEDERATION_VERSIONS


def is_supported_in_federation_version(version: str) -> bool:
    """Return whether a feature introduced in `version` is available in the current `FEDERATION_VERSION`."""
    return parse_version(undine_settings.FEDERATION_VERSION) >= parse_version(version)


def parse_version(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def get_federation_spec_url() -> str:
    return f"https://specs.apollo.dev/federation/v{undine_settings.FEDERATION_VERSION}"
