"""Contains utility functions for dealing with Django models and the ORM."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

from django.core.exceptions import FieldDoesNotExist
from django.db.models.constants import LOOKUP_SEP

from undine.errors.exceptions import (
    GraphQLModelNotFoundError,
    GraphQLMultipleObjectsFoundError,
    ModelFieldDoesNotExistError,
    ModelFieldNotARelationError,
)
from undine.settings import undine_settings

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
    from django.db import models

    from undine.typing import TModel


__all__ = [
    "generic_foreign_key_for_generic_relation",
    "generic_relations_for_generic_foreign_key",
    "get_instance_or_raise",
    "get_lookup_field_name",
    "get_model_field",
]


def get_instance_or_raise(*, model: type[TModel], key: str, value: Any) -> TModel:
    """Get model by the given key with the given value. Raise GraphQL errors appropriately."""
    try:
        return model._default_manager.get(**{key: value})
    except model.DoesNotExist as error:
        raise GraphQLModelNotFoundError(key=key, value=value, model=model) from error
    except model.MultipleObjectsReturned as error:
        raise GraphQLMultipleObjectsFoundError(key=key, value=value, model=model) from error


def generic_relations_for_generic_foreign_key(fk: GenericForeignKey) -> Generator[GenericRelation, None, None]:
    """Get all GenericRelations for the given GenericForeignKey."""
    from django.contrib.contenttypes.fields import GenericRelation

    return (field for field in fk.model._meta._relation_tree if isinstance(field, GenericRelation))


def generic_foreign_key_for_generic_relation(relation: GenericRelation) -> GenericForeignKey:
    """Get the GenericForeignKey for the given GenericRelation."""
    from django.contrib.contenttypes.fields import GenericForeignKey

    return next(
        field
        for field in relation.related_model._meta.get_fields()
        if (
            isinstance(field, GenericForeignKey)
            and field.fk_field == relation.object_id_field_name
            and field.ct_field == relation.content_type_field_name
        )
    )


def get_model_field(*, model: type[models.Model], lookup: str) -> models.Field:
    """
    Gets a model field from the given lookup string.

    :param model: Django model to start finding the field from.
    :param lookup: Lookup string using Django's lookup syntax. E.g. "foo__bar__baz".
    """
    parts = lookup.split(LOOKUP_SEP)
    last = len(parts)
    field: models.Field | None = None

    for part_num, part in enumerate(parts, start=1):
        if part == "pk":
            field = model._meta.pk
        else:
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist as error:
                raise ModelFieldDoesNotExistError(field=part, model=model) from error

        if part_num == last:
            break

        if not field.is_relation:
            raise ModelFieldNotARelationError(field=part, model=model)

        model = field.related_model

    if field is None:  # pragma: no cover
        raise ModelFieldDoesNotExistError(field=lookup, model=model) from None

    return field


def get_lookup_field_name(model: type[models.Model]) -> str:
    return "pk" if undine_settings.USE_PK_FIELD_NAME else model._meta.pk.name
