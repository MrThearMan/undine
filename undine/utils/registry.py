from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db import models

    from undine import ModelGQLType


__all__ = [
    "TYPE_REGISTRY",
]


TYPE_REGISTRY: dict[type[models.Model], type[ModelGQLType]] = {}
"""
Maps Django model classes to their corresponding `ModelGQLTypes`.
This allows deferring the creation of field resolvers for related fields,
which would use a `ModelGQLType` that is not created when the field is defined.
"""
