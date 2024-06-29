from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import FieldDoesNotExist
from django.db.models.constants import LOOKUP_SEP

from undine.utils import dotpath

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
    :raises ValueError: Could not find the field with the given arguments.
    """
    parts = lookup.split(LOOKUP_SEP)

    last_part = len(parts)
    for part_num, part in enumerate(parts, start=1):
        if part == "pk":
            field = model._meta.pk
        else:
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist as error:
                msg = f"Field '{part}' does not exist in model '{dotpath(model)}'."
                raise ValueError(msg) from error

        if part_num == last_part:
            return field

        if not field.is_relation:
            msg = f"Field '{part}' is not a relation in model '{dotpath(model)}'."
            raise ValueError(msg)

        model = field.related_model

    msg = f"Unknonwn error: model='{dotpath(model)}', field_name='{lookup}'."
    raise ValueError(msg)
