from __future__ import annotations

from typing import TYPE_CHECKING, Any, Container, Iterable

from graphql import GraphQLInputField, GraphQLInputObjectType, Undefined

from undine.errors import MissingModelError
from undine.fields import Filter
from undine.settings import undine_settings
from undine.utils.reflection import get_members
from undine.utils.text import get_docstring, get_schema_name

if TYPE_CHECKING:
    from django.db import models

    from undine.modelgql.model_filter import ModelGQLFilter


__all__ = [
    "ModelGQLFilterMeta",
]


class ModelGQLFilterMeta(type):
    """A metaclass that modifies how a `ModelGQLFilter` is created."""

    def __new__(  # noqa: PLR0913
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        auto_filters: bool = True,
        exclude: Iterable[str] = (),
        name: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelGQLFilterMeta:
        """See `ModelGQLFilter` for documentation of arguments."""
        if model is Undefined:  # Early return for the `ModelGQLFilter` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="ModelGQLFilter")

        if auto_filters:
            _attrs |= get_filters_for_model(model, exclude=set(exclude) | set(_attrs))

        # Add model to attrs before class creation so that it's available during `Filter.__set_name__`.
        _attrs["__model__"] = model
        instance: type[ModelGQLFilter] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible filter names.
        instance.__model__ = model
        instance.__filter_map__ = {get_schema_name(name): ftr for name, ftr in get_members(instance, Filter)}
        instance.__input_type__ = get_input_object_type_for_model_filter(instance, name=name, extensions=extensions)
        return instance


def get_input_object_type_for_model_filter(
    instance: type[ModelGQLFilter],
    *,
    name: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLInputObjectType:
    """
    Create the InputObjectType argument for the given `ModelGQLFilter`

    `InputObjectType` should be created once, since GraphQL schema cannot
    contain multiple types with the same name.
    """
    if name is None:
        name = instance.__name__
    if extensions is None:
        extensions = {}

    input_object_type = GraphQLInputObjectType(
        name=name,
        description=get_docstring(instance),
        fields={},
        extensions={
            **extensions,
            undine_settings.FILTER_INPUT_EXTENSIONS_KEY: instance,
        },
    )

    def _get_fields() -> dict[str, GraphQLInputField]:
        fields = {name: filter_.as_input_field() for name, filter_ in instance.__filter_map__.items()}
        fields["AND"] = fields["OR"] = fields["NOT"] = fields["XOR"] = GraphQLInputField(type_=input_object_type)
        return fields

    input_object_type._fields = _get_fields
    return input_object_type


def get_filters_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Filter]:
    """Creates 'Filter's for all of the given model's non-related fields, except those in the 'exclude' list."""
    result: dict[str, Filter] = {}
    for model_field in model._meta._get_fields(reverse=False):
        if model_field.is_relation:
            continue

        field_name = model_field.name
        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if undine_settings.USE_PK_FIELD_NAME and is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        for lookup_expr in model_field.get_lookups():
            result[f"{field_name}_{lookup_expr}"] = Filter(field_name, lookup_expr=lookup_expr)

    return result
