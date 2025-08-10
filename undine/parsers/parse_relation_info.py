from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from undine.converters import convert_to_python_type
from undine.dataclasses import RelInfo
from undine.typing import RelationType
from undine.utils.model_utils import generic_foreign_key_for_generic_relation, get_related_name

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericRelation
    from django.db.models import Field, ForeignKey, Model

    from undine.typing import ForwardField, GenericField, RelatedField, ReverseField

__all__ = [
    "parse_model_relation_info",
]


@cache
def parse_model_relation_info(*, model: type[Model]) -> dict[str, RelInfo]:
    relation_info: dict[str, RelInfo] = {}

    for field in model._meta.get_fields():
        if not field.is_relation:
            continue

        related_field: RelatedField | GenericField = field  # type: ignore[assignment]
        relation_type = RelationType.for_related_field(related_field)

        if relation_type.is_generic_relation:
            generic_rel_field: GenericRelation = related_field  # type: ignore[assignment]
            generic_fk_field = generic_foreign_key_for_generic_relation(generic_rel_field)
            name = generic_rel_field.name

            fk_field: Field = generic_fk_field.model._meta.get_field(generic_fk_field.fk_field)  # type: ignore[assignment]
            ct_field: ForeignKey = generic_fk_field.model._meta.get_field(generic_fk_field.ct_field)  # type: ignore[assignment]

            relation_info[name] = RelInfo(
                relation_type=relation_type,
                #
                # Source details
                field_name=name,
                model=model,
                model_pk_type=convert_to_python_type(fk_field),  # Type of the fk field, not related model pk.
                nullable=True,  # Reverse fields are always nullable.
                #
                # Target details
                related_name=generic_fk_field.name,
                related_model=generic_fk_field.model,
                related_model_pk_type=convert_to_python_type(generic_fk_field.model._meta.pk),
                related_nullable=fk_field.null and ct_field.null,
            )
            continue

        if relation_type.is_generic_foreign_key:
            # For GenericForeignKey, there are multiple related models,
            # so we don't have a single model or related name.
            generic_fk_field = related_field  # type: ignore[assignment]
            name = generic_fk_field.name

            fk_field = generic_fk_field.model._meta.get_field(generic_fk_field.fk_field)  # type: ignore[assignment]
            ct_field = generic_fk_field.model._meta.get_field(generic_fk_field.ct_field)  # type: ignore[assignment]

            relation_info[name] = RelInfo(
                relation_type=relation_type,
                #
                # Source details
                field_name=name,
                model=model,
                model_pk_type=convert_to_python_type(model._meta.pk),
                nullable=fk_field.null and ct_field.null,
                #
                # Target details
                #
                # For GenericForeignKey, there are multiple related models,
                # so we don't have a single model or related name.
                related_name=None,
                related_model=None,
                related_model_pk_type=convert_to_python_type(fk_field),  # Type of the fk field, not related model pk.
                related_nullable=True,  # Reverse fields are always nullable.
            )
            continue

        if relation_type.is_forward:
            forward_field: ForwardField = related_field  # type: ignore[assignment]
            related_model = forward_field.remote_field.model
            name = forward_field.name

            nullable = True if relation_type.is_many_to_many else forward_field.null

            is_self_relation = model == related_model

            relation_info[name] = RelInfo(
                relation_type=relation_type,
                #
                # Source details
                field_name=name,
                model=model,
                model_pk_type=convert_to_python_type(model._meta.pk),
                nullable=nullable,
                #
                # Target details
                related_name=get_related_name(field if is_self_relation else field.remote_field),  # type: ignore[arg-type]
                related_model=related_model,
                related_model_pk_type=convert_to_python_type(related_model._meta.pk),
                related_nullable=True,  # Reverse fields are always nullable
            )
            continue

        if relation_type.is_reverse:
            reverse_field: ReverseField = related_field  # type: ignore[assignment]
            forward_field = reverse_field.remote_field  # type: ignore[assignment]
            name = get_related_name(reverse_field)

            nullable = True if relation_type.is_many_to_many else forward_field.null

            relation_info[name] = RelInfo(
                relation_type=relation_type,
                #
                # Source details
                field_name=name,
                model=model,
                model_pk_type=convert_to_python_type(model._meta.pk),
                nullable=True,  # Reverse fields are always nullable
                #
                # Target details
                related_name=forward_field.name,
                related_model=forward_field.model,
                related_model_pk_type=convert_to_python_type(forward_field.model._meta.pk),
                related_nullable=nullable,
            )
            continue

        msg = f"Unhandled relation type: {relation_type}"  # pragma: no cover
        raise NotImplementedError(msg)  # pragma: no cover

    return relation_info
