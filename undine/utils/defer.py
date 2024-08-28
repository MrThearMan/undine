from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from undine.errors import MissingDeferredGQLTypeError

from .reflection import generic_relations_for_generic_foreign_key
from .registry import TYPE_REGISTRY

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db import models

    from undine import ModelGQLType
    from undine.typing import RelatedField


__all__ = [
    "DeferredModelGQLType",
    "DeferredModelGQLTypeUnion",
]


@dataclass(frozen=True, slots=True)
class DeferredModelGQLType:
    """Represents a lazily evaluated ModelGQLType for a related field."""

    get_type: Callable[[], type[ModelGQLType]]
    name: str
    description: str | None
    nullable: bool
    many: bool
    model: type[models.Model]

    @classmethod
    def for_related_field(cls, field: RelatedField) -> DeferredModelGQLType:
        name = field.name
        description = getattr(field, "help_text", None) or None
        nullable = field.null is True
        many = bool(field.many_to_many or field.one_to_many)
        model = field.related_model

        def inner() -> type[ModelGQLType]:
            value = TYPE_REGISTRY.get(model)
            if value is None:
                raise MissingDeferredGQLTypeError(name=name, model=model)

            return value

        return cls(get_type=inner, name=name, description=description, nullable=nullable, many=many, model=model)


@dataclass(frozen=True, slots=True)
class DeferredModelGQLTypeUnion:
    """Represents a lazily evaluated ModelGQLType for a related field."""

    get_types: Callable[[], list[type[ModelGQLType]]]
    name: str
    description: str | None
    model: type[models.Model]

    @classmethod
    def for_generic_foreign_key(cls, field: GenericForeignKey) -> DeferredModelGQLTypeUnion:
        name = field.name
        model = field.model
        deferred_types = [
            DeferredModelGQLType.for_related_field(field.remote_field)
            for field in generic_relations_for_generic_foreign_key(field)
        ]

        def inner() -> list[type[ModelGQLType]]:
            return [deferred_type.get_type() for deferred_type in deferred_types]

        return cls(get_types=inner, name=name, description=None, model=model)


@dataclass(frozen=True, slots=True)
class DeferredModelGQLMutation:  # TODO: implement
    """Represents a lazily evaluated ModelGQLMutation for a related field."""

    @classmethod
    def for_related_field(cls, field: RelatedField) -> DeferredModelGQLMutation:
        pass
