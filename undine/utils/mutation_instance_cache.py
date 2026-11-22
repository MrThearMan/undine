from __future__ import annotations

from typing import TYPE_CHECKING, Any

from undine.utils.model_utils import get_instances_or_raise

if TYPE_CHECKING:
    from django.db.models import Model

    from undine.typing import MutationInstanceCache


__all__ = [
    "add_cached_instance",
    "fetch_instances",
    "get_cached_instance",
]


def get_cached_instance[T: Model](cache: MutationInstanceCache | None, *, model: type[T], pk: Any) -> T | None:
    """Get an existing instance from the cache, if it has been fetched already."""
    if cache is None or pk is None:
        return None
    return cache.instances.get((model, pk))  # type: ignore[return-value]


def add_cached_instance(cache: MutationInstanceCache | None, instance: Model) -> None:
    """Add an existing instance to the cache."""
    if cache is None or instance.pk is None:
        return
    cache.instances[type(instance), instance.pk] = instance


def fetch_instances[T: Model](cache: MutationInstanceCache | None, *, model: type[T], pks: list[Any]) -> dict[Any, T]:
    """
    Get existing instances for the given primary keys, by primary key.
    Only instances missing from the cache are fetched, in one query.

    :raises GraphQLModelNotFoundError: If an instance for the given primary key does not exist.
    :raises GraphQLModelsNotFoundError: If instances for many of the given primary keys do not exist.
    """
    instance_map: dict[Any, T] = {}
    missing: list[Any] = []
    for pk in dict.fromkeys(pks):
        cached = get_cached_instance(cache, model=model, pk=pk)
        if cached is None:
            missing.append(pk)
        else:
            instance_map[pk] = cached

    if missing:
        for instance in get_instances_or_raise(model=model, pks=missing):
            add_cached_instance(cache, instance)
            instance_map[instance.pk] = instance

    return instance_map
