from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from django.db import models
from graphql import GraphQLEnumType, GraphQLEnumValue, Undefined

from undine.errors import MissingModelError
from undine.fields import Ordering, get_orderings_for_model
from undine.settings import undine_settings
from undine.utils.reflection import get_members
from undine.utils.text import get_docstring, get_schema_name

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
        instance.__ordering_enum__ = get_enum_type_for_model_ordering(instance, name=name, extensions=extensions)
        return instance


def get_enum_type_for_model_ordering(
    instance: type[ModelGQLOrdering],
    *,
    name: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLEnumType:
    """
    Create the ordering `GraphQLEnum` argument for the given `ModelGQLOrdering`.

    `GraphQLEnum` should be created once, since a GraphQL schema cannot
    contain multiple types with the same name.
    """
    if name is None:
        name = instance.__name__
    if extensions is None:
        extensions = {}

    enum_values: dict[str, GraphQLEnumValue] = {}
    for name_, ordering_ in instance.__ordering_map__.items():
        if not ordering_.supports_reversing:
            enum_values[name_] = GraphQLEnumValue(value=name_, description=ordering_.description)
            continue

        for direction in ("Asc", "Desc"):
            schema_name = f"{name_}{direction}"
            enum_values[schema_name] = GraphQLEnumValue(value=schema_name, description=ordering_.description)

    return GraphQLEnumType(
        name=name,
        values=enum_values,
        description=get_docstring(instance),
        extensions={
            **extensions,
            undine_settings.ORDER_BY_EXTENSIONS_KEY: instance,
        },
    )
