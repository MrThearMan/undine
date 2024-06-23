# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models

from undine.parsers import parse_parameters
from undine.settings import undine_settings
from undine.typing import Parameter, Ref
from undine.utils import TypeMapper

from .field_to_type import convert_model_field_to_type

__all__ = [
    "convert_ref_to_params",
]


convert_ref_to_params = TypeMapper[Ref, list[Parameter]]()


@convert_ref_to_params.register
def convert_function(ref: FunctionType, **kwargs: Any) -> list[Parameter]:
    return parse_parameters(ref, level=2)


@convert_ref_to_params.register
def convert_property(ref: property, **kwargs: Any) -> list[Parameter]:
    return []


@convert_ref_to_params.register
def convert_model_field(ref: models.Field, **kwargs: Any) -> list[Parameter]:
    return []


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion, ModelGQLType

    @convert_ref_to_params.register
    def convert_model_node(ref: type[ModelGQLType], *, many: bool, top_level: bool) -> list[Parameter]:
        if many:
            return ref.__get_filters__()

        # Field defined in the 'Query' class.
        if top_level:
            field = ref.__lookup_field__
            field_name = "pk" if field.primary_key and undine_settings.USE_PK_FIELD_NAME else field.name
            field_type = convert_model_field_to_type(field)
            return [Parameter(name=field_name, annotation=field_type)]

        return []

    @convert_ref_to_params.register
    def convert_deferred_type(ref: DeferredModelGQLType, **kwargs: Any) -> list[Parameter]:
        return convert_model_node(ref.get_type(), **kwargs)

    @convert_ref_to_params.register
    def convert_deferred_type_union(ref: DeferredModelGQLTypeUnion, **kwargs: Any) -> list[Parameter]:
        # TODO: Union args?
        return []
