from __future__ import annotations

from typing import TYPE_CHECKING, Any, Container, Iterable

from django.db import models
from graphql import Undefined

from undine.errors.exceptions import MissingModelError
from undine.fields import Ordering
from undine.settings import undine_settings
from undine.utils.reflection import get_members
from undine.utils.text import get_schema_name

if TYPE_CHECKING:
    from undine.modelgql.model_ordering import ModelGQLOrdering

__all__ = [
    "ModelGQLOrderingMeta",
]


class ModelGQLOrderingMeta(type):
    """A metaclass that modifies how a `ModelGQLOrdering` is created."""

    def __new__(  # noqa: PLR0913
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        auto_ordering: bool = True,
        exclude: Iterable[str] = (),
        name: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelGQLOrderingMeta:
        """See `ModelGQLOrdering` for documentation of arguments."""
        if model is Undefined:  # Early return for the `ModelGQLOrdering` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if models is None:
            raise MissingModelError(name=_name, cls="ModelGQLOrdering")

        if auto_ordering:
            _attrs |= get_orderings_for_model(model, exclude=set(exclude) | set(_attrs))

        # Add model to attrs before class creation so that it's available during `Ordering.__set_name__`.
        _attrs["__model__"] = model
        instance: type[ModelGQLOrdering] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible ordering names.
        instance.__model__ = model
        instance.__ordering_map__ = {get_schema_name(n): o for n, o in get_members(instance, Ordering)}
        instance.__typename__ = name or _name
        instance.__extensions__ = extensions or {} | {undine_settings.ORDER_BY_EXTENSIONS_KEY: instance}
        return instance


def get_orderings_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Ordering]:
    """Creates 'Ordering's for all of the given model's non-related fields, except those in the 'exclude' list."""
    result: dict[str, Ordering] = {}
    for model_field in model._meta._get_fields(reverse=False):
        if model_field.is_relation:
            continue

        field_name = model_field.name
        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if undine_settings.USE_PK_FIELD_NAME and is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        result[field_name] = Ordering(field_name)

    return result
