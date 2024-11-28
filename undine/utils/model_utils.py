from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator, TypeGuard

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

    from undine.typing import ModelField, TModel, ToManyField, ToOneField

__all__ = [
    "generic_foreign_key_for_generic_relation",
    "generic_relations_for_generic_foreign_key",
    "get_instance_or_raise",
    "get_lookup_field_name",
    "get_model_field",
    "is_to_many",
    "is_to_one",
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
    from django.contrib.contenttypes.fields import GenericRelation  # noqa: PLC0415

    return (field for field in fk.model._meta._relation_tree if isinstance(field, GenericRelation))


def generic_foreign_key_for_generic_relation(relation: GenericRelation) -> GenericForeignKey:
    """Get the GenericForeignKey for the given GenericRelation."""
    from django.contrib.contenttypes.fields import GenericForeignKey  # noqa: PLC0415

    return next(
        field
        for field in relation.related_model._meta.get_fields()
        if (
            isinstance(field, GenericForeignKey)
            and field.fk_field == relation.object_id_field_name
            and field.ct_field == relation.content_type_field_name
        )
    )


def get_model_field(*, model: type[models.Model], lookup: str) -> ModelField:
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
                if not part.endswith("_set"):
                    raise ModelFieldDoesNotExistError(field=part, model=model) from error

                # Field might be a reverse many-related field without `related_name`, in which case
                # the `model._meta.fields_map` will store the relation without the "_set" suffix.
                try:
                    field = model._meta.get_field(part.removesuffix("_set"))
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


def get_model_fields_for_graphql(
    model: type[models.Model],
    *,
    include_relations: bool = True,
    include_nonsaveable: bool = True,
) -> Generator[models.Field, None, None]:
    """
    Get all fields from the model that should be included in a GraphQL schema.

    :param model: The model to get fields from.
    :param include_relations: Whether to include relation fields.
    :param include_nonsaveable: Whether to include fields that are not editable or not concrete.
    """
    for model_field in model._meta._get_fields():
        is_relation = bool(getattr(model_field, "is_relation", False))  # Does field reference a relation?
        editable = bool(getattr(model_field, "editable", True))  # Is field value editable by users?
        concrete = bool(getattr(model_field, "concrete", True))  # Does field correspond to a db column?

        if is_relation:
            if include_relations:
                yield model_field
            continue

        if not include_nonsaveable and (not editable or not concrete):
            continue

        yield model_field


def get_lookup_field_name(model: type[models.Model]) -> str:
    return "pk" if undine_settings.USE_PK_FIELD_NAME else model._meta.pk.name


def is_to_many(field: models.Field) -> TypeGuard[ToManyField]:
    return bool(field.one_to_many or field.many_to_many)


def is_to_one(field: models.Field) -> TypeGuard[ToOneField]:
    return bool(field.many_to_one or field.one_to_one)
