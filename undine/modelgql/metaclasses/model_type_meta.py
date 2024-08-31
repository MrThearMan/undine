from __future__ import annotations

from typing import TYPE_CHECKING, Any, Container, Iterable, Literal

from graphql import GraphQLObjectType, Undefined

from undine.errors import MismatchingModelError, MissingModelError
from undine.fields import Field
from undine.settings import undine_settings
from undine.utils.reflection import get_members
from undine.utils.registry import TYPE_REGISTRY
from undine.utils.text import get_docstring, get_schema_name

if TYPE_CHECKING:
    from django.db import models

    from undine.modelgql.model_filter import ModelGQLFilter
    from undine.modelgql.model_ordering import ModelGQLOrdering
    from undine.modelgql.model_type import ModelGQLType


__all__ = [
    "ModelGQLTypeMeta",
]


class ModelGQLTypeMeta(type):
    """A metaclass that modifies how a `ModelGQLType` is created."""

    def __new__(  # noqa: PLR0913
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        filters: type[ModelGQLFilter] | Literal[True] | None = None,
        ordering: type[ModelGQLOrdering] | Literal[True] | None = None,
        auto_fields: bool = True,
        exclude: Iterable[str] = (),
        lookup_field: str | None = "pk",
        name: str | None = None,
        register: bool = True,
        extensions: dict[str, Any] | None = None,
    ) -> ModelGQLTypeMeta:
        """See `ModelGQLType` for documentation of arguments."""
        if model is Undefined:  # Early return for the `ModelGQLType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="ModelGQLType")

        if auto_fields:
            _attrs |= get_fields_for_model(model, exclude=set(exclude) | set(_attrs))

        if filters is True:
            from undine import ModelGQLFilter

            filters = type(f"{model.__name__}Filter", (ModelGQLFilter,), {}, model=model)

        if filters is not None and filters.__model__ is not model:
            raise MismatchingModelError(
                cls=filters.__name__,
                bad_model=model,
                type=_name,
                expected_model=filters.__model__,
            )

        if ordering is True:
            from undine import ModelGQLOrdering

            ordering = type(f"{model.__name__}Ordering", (ModelGQLOrdering,), {}, model=model)

        if ordering is not None and ordering.__model__ is not model:
            raise MismatchingModelError(
                cls=ordering.__name__,
                bad_model=model,
                type=_name,
                expected_model=ordering.__model__,
            )

        # Add model to attrs before class creation so that it's available during `Field.__set_name__`.
        _attrs["__model__"] = model
        instance: type[ModelGQLType] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        if register:
            TYPE_REGISTRY[model] = instance

        # Members should use '__dunder__' names to avoid name collisions with possible field names.
        instance.__model__ = model
        instance.__filters__ = filters
        instance.__ordering__ = ordering
        instance.__field_map__ = {get_schema_name(name): field for name, field in get_members(instance, Field)}
        instance.__lookup_field__ = lookup_field
        instance.__output_type__ = get_output_object_type_model_type(instance, name=name, extensions=extensions)
        return instance


def get_output_object_type_model_type(
    instance: type[ModelGQLType],
    *,
    name: str | None = None,
    extensions: dict[str, Any] | None,
) -> GraphQLObjectType:
    """
    Creates the GraphQL ObjectType for this `ModelGQLType`.

    ObjectType should be created once, since GraphQL schema cannot
    contain multiple types with the same name.
    """
    if name is None:
        name = instance.__name__
    if extensions is None:
        extensions = {}

    return GraphQLObjectType(
        name=name,
        # Give fields as a callable to delay their creation.
        # This gives time for all ModelGQLTypes to be registered.
        fields=lambda: {name: field.get_graphql_field() for name, field in instance.__field_map__.items()},
        description=get_docstring(instance),
        is_type_of=instance.__is_type_of__,
        extensions={
            **extensions,
            undine_settings.MODEL_TYPE_EXTENSIONS_KEY: instance,
        },
    )


def get_fields_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Field]:
    """Add 'Field's for all of the given model's fields, except those in the 'exclude' list."""
    result: dict[str, Field] = {}
    for model_field in model._meta._get_fields():
        field_name = model_field.name
        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if undine_settings.USE_PK_FIELD_NAME and is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        result[field_name] = Field(model_field)

    return result
