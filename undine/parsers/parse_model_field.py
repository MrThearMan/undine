from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import FieldDoesNotExist
from django.db.models.constants import LOOKUP_SEP

from undine.errors import ModelFieldDoesNotExistError, ModelFieldNotARelationError

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "parse_model_field",
]


def parse_model_field(*, model: type[models.Model], lookup: str) -> models.Field:
    """
    Parses a model field from the given lookup string.

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

    if field is None:
        raise ModelFieldDoesNotExistError(field=lookup, model=model) from None

    return field
