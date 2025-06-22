from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from django.db.models import Field, Model


__all__ = [
    "get_translatable_fields",
    "is_translation_field",
]


try:
    from modeltranslation.fields import TranslationField
except ImportError:
    TranslationField = type("TranslationField", (), {})  # type: ignore[misc,assignment]


def is_translation_field(field: Field) -> TypeGuard[TranslationField]:
    return isinstance(field, TranslationField)


def get_translatable_fields(model: type[Model]) -> set[str]:
    """If `django-modeltranslation` is installed, find all translatable fields in the given model."""
    try:
        from modeltranslation.manager import get_translatable_fields_for_model  # noqa: PLC0415
    except ImportError:
        return set()

    return set(get_translatable_fields_for_model(model) or [])
