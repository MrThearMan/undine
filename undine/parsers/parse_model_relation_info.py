from __future__ import annotations

import enum
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from django.db import models
from graphql import Undefined

from undine.utils.text import to_camel_case

if TYPE_CHECKING:
    from undine.typing import RelatedField

__all__ = [
    "RelatedFieldInfo",
    "RelationType",
    "parse_model_relation_info",
]


@cache
def parse_model_relation_info(*, model: type[models.Model]) -> dict[str, RelatedFieldInfo]:
    from undine.converters import convert_model_field_to_type

    relation_info: dict[str, RelatedFieldInfo] = {}

    for field in model._meta.get_fields():
        # Skip non-relation fields.
        if field.is_relation is False:
            continue

        relation_type = RelationType.for_related_field(field)

        related_model_pk_type = None  # Unknown for GenericForeignKey since there can be many relations.
        if field.related_model is not None:
            related_model_pk_type = convert_model_field_to_type(field.related_model._meta.pk)

        if relation_type.is_forward:
            field_name = field.name
            related_name = field.remote_field.get_accessor_name()
            if related_name is None:  # Self-referential relation
                related_name = field_name
            related_model = field.related_model
            nullable: bool = getattr(field, "null", False)

        elif relation_type.is_reverse:
            field_name = field.get_accessor_name()
            related_name = field.remote_field.name
            related_model = field.related_model
            nullable: bool = getattr(field.remote_field, "null", False)

        elif relation_type.is_generic_relation:
            field_name = field.name
            # Find the GenericForeignKey field name that points to this model.
            related_name = next(
                related_field.name
                for related_field in field.related_model._meta.get_fields()
                if getattr(related_field, "fk_field", Undefined) == field.object_id_field_name
            )
            related_model = field.related_model
            nullable: bool = getattr(field, "null", False)

        elif relation_type.is_generic_foreign_key:
            field_name = field.name
            # For GenericForeignKey, there are multiple related models,
            # so we don't have a single model or related name.
            related_name = None
            related_model = None
            nullable: bool = getattr(field, "null", False)

        else:  # pragma: no cover
            msg = f"Unhandled relation type: {relation_type}"
            raise NotImplementedError(msg)

        relation_info[to_camel_case(field_name)] = RelatedFieldInfo(
            field_name=field_name,
            related_name=related_name,
            relation_type=relation_type,
            nullable=nullable,
            related_model_pk_type=related_model_pk_type,
            model=related_model,
        )

    return relation_info


class RelationType(enum.Enum):
    REVERSE_ONE_TO_ONE = "REVERSE_ONE_TO_ONE"
    FORWARD_ONE_TO_ONE = "FORWARD_ONE_TO_ONE"
    FORWARD_MANY_TO_ONE = "FORWARD_MANY_TO_ONE"
    REVERSE_ONE_TO_MANY = "REVERSE_ONE_TO_MANY"
    REVERSE_MANY_TO_MANY = "REVERSE_MANY_TO_MANY"
    FORWARD_MANY_TO_MANY = "FORWARD_MANY_TO_MANY"
    GENERIC_ONE_TO_MANY = "GENERIC_ONE_TO_MANY"
    GENERIC_MANY_TO_ONE = "GENERIC_MANY_TO_ONE"

    @classmethod
    def for_related_field(cls, field: RelatedField) -> RelationType:
        try:
            return _related_field_to_relation_type_map()[type(field)]
        except KeyError as error:
            msg = f"Unknown related field: {field} (of type {type(field)})"
            raise ValueError(msg) from error

    @enum.property
    def is_reverse(self) -> bool:
        return self in (
            RelationType.REVERSE_ONE_TO_ONE,
            RelationType.REVERSE_ONE_TO_MANY,
            RelationType.REVERSE_MANY_TO_MANY,
        )

    @enum.property
    def is_forward(self) -> bool:
        return self in (
            RelationType.FORWARD_ONE_TO_ONE,
            RelationType.FORWARD_MANY_TO_ONE,
            RelationType.FORWARD_MANY_TO_MANY,
        )

    @enum.property
    def is_generic_relation(self) -> bool:
        return self == RelationType.GENERIC_ONE_TO_MANY

    @enum.property
    def is_generic_foreign_key(self) -> bool:
        return self == RelationType.GENERIC_MANY_TO_ONE

    @enum.property
    def created_before(self) -> bool:
        """These relations need to be created before the main model is created."""
        return self in (
            RelationType.FORWARD_ONE_TO_ONE,
            RelationType.FORWARD_MANY_TO_ONE,
        )

    @enum.property
    def created_after(self) -> bool:
        """These relations need to be created after the main model is created."""
        return self in (
            RelationType.REVERSE_ONE_TO_ONE,
            RelationType.REVERSE_ONE_TO_MANY,
            RelationType.REVERSE_MANY_TO_MANY,
            RelationType.FORWARD_MANY_TO_MANY,
            RelationType.GENERIC_ONE_TO_MANY,
        )


@cache
def _related_field_to_relation_type_map() -> dict[type[RelatedField], RelationType]:
    # Must defer creating this map, since the 'contenttypes' app needs to be loaded first.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    return {
        models.OneToOneRel: RelationType.REVERSE_ONE_TO_ONE,  # e.g. Reverse OneToOneField
        models.ManyToOneRel: RelationType.REVERSE_ONE_TO_MANY,
        models.ManyToManyRel: RelationType.REVERSE_MANY_TO_MANY,  # e.g. Reverse ManyToManyField
        models.OneToOneField: RelationType.FORWARD_ONE_TO_ONE,
        models.ForeignKey: RelationType.FORWARD_MANY_TO_ONE,
        models.ManyToManyField: RelationType.FORWARD_MANY_TO_MANY,
        GenericRelation: RelationType.GENERIC_ONE_TO_MANY,
        GenericForeignKey: RelationType.GENERIC_MANY_TO_ONE,
    }


@dataclass(frozen=True, slots=True)
class RelatedFieldInfo:
    """Holds information about a related field on a model."""

    field_name: str
    related_name: str | None
    relation_type: RelationType
    nullable: bool
    related_model_pk_type: type | None
    model: type[models.Model] | None
