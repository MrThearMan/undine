from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from django.db.models import Field, Model


with suppress(ImportError):
    from modeltranslation.fields import TranslationField
    from modeltranslation.manager import get_translatable_fields_for_model


__all__ = [
    "get_translatable_fields",
    "is_translation_field",
]


IS_MODELTRANSLATION_INSTALLED: bool = "TranslationField" in globals()


def is_translation_field(field: Field) -> TypeGuard[TranslationField]:
    if not IS_MODELTRANSLATION_INSTALLED:
        return False

    return isinstance(field, TranslationField)


def get_translatable_fields(model: type[Model]) -> set[str]:
    """If `django-modeltranslation` is installed, find all translatable fields in the given model."""
    if not IS_MODELTRANSLATION_INSTALLED:
        return set()

    return set(get_translatable_fields_for_model(model) or [])
