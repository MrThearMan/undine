from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .reflection import generic_relations_for_generic_foreign_key
from .registry import TYPE_REGISTRY

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine import ModelGQLType
    from undine.typing import RelatedField


__all__ = [
    "DeferredModelGQLType",
    "DeferredModelGQLTypeUnion",
]


@dataclass(frozen=True, slots=True)
class DeferredModelGQLType:
    """Represents a lazily evaluated ModelGQLType for a related field."""

    field: RelatedField

    def get_type(self) -> type[ModelGQLType]:
        return TYPE_REGISTRY[self.field.related_model]


@dataclass(frozen=True, slots=True)
class DeferredModelGQLTypeUnion:
    """Represents a lazily evaluated ModelGQLType for a related field."""

    field: GenericForeignKey

    def get_types(self) -> list[type[ModelGQLType]]:
        return [
            TYPE_REGISTRY[field.remote_field.related_model]
            for field in generic_relations_for_generic_foreign_key(self.field)
        ]
