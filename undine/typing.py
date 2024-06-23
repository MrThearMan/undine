from __future__ import annotations

from dataclasses import dataclass
from types import FunctionType
from typing import TYPE_CHECKING, Any, TypeAlias, TypedDict, Union

from django.db import models
from graphql import Undefined

if TYPE_CHECKING:
    from undine.types import DeferredModelGQLType, ModelGQLType


__all__ = [
    "FieldParams",
    "Ref",
    "ToManyField",
    "ToOneField",
]

Ref: TypeAlias = Union[
    models.Field,  #
    FunctionType,
    property,
    type["ModelGQLType"],
    "DeferredModelGQLType",
]


class FieldParams(TypedDict):
    description: str | None
    deprecation_reason: str | None
    extensions: dict[str, Any] | None
    nullable: bool
    many: bool


ToOneField = models.OneToOneField | models.OneToOneRel | models.ForeignKey
ToManyField = models.ManyToManyField | models.ManyToManyRel | models.ManyToOneRel


@dataclass
class Parameter:
    name: str
    annotation: type
    default_value: Any = Undefined
