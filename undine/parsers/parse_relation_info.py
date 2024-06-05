from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from undine.converters import convert_to_python_type
from undine.dataclasses import RelInfo
from undine.typing import RelationType
from undine.utils.model_utils import generic_foreign_key_for_generic_relation

if TYPE_CHECKING:
    from django.db.models import Model

__all__ = [
    "parse_model_relation_info",
]


@cache
def parse_model_relation_info(*, model: type[Model]) -> dict[str, RelInfo]:
    relation_info: dict[str, RelInfo] = {}

    for field in model._meta.get_fields():
        # Skip non-relation fields.
        if field.is_relation is False:
            continue

        relation_type = RelationType.for_related_field(field)

        is_generic_foreign_key = hasattr(field, "fk_field")  # No need to import 'GenericForeignKey' inline
        fk_field = model._meta.get_field(field.fk_field) if is_generic_foreign_key else field.related_model._meta.pk
        related_model_pk_type = convert_to_python_type(fk_field)

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
            nullable = getattr(field.remote_field, "null", False)

        elif relation_type.is_generic_relation:
            field_name = field.name
            # Find the GenericForeignKey field name that points to this model.
            related_name = generic_foreign_key_for_generic_relation(field).name
            related_model = field.related_model
            nullable = getattr(field, "null", False)

        elif relation_type.is_generic_foreign_key:
            field_name = field.name
            # For GenericForeignKey, there are multiple related models,
            # so we don't have a single model or related name.
            related_name = None
            related_model = None
            nullable = getattr(field, "null", False)

        else:  # pragma: no cover
            msg = f"Unhandled relation type: {relation_type}"
            raise NotImplementedError(msg)

        relation_info[field_name] = RelInfo(
            field_name=field_name,
            related_name=related_name,
            relation_type=relation_type,
            nullable=nullable,
            related_model_pk_type=related_model_pk_type,
            model=related_model,
        )

    return relation_info
