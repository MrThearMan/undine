from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLBoolean, GraphQLInputType

from undine.parsers import parse_first_param_type, parse_model_field
from undine.typing import FieldRef
from undine.utils import TypeDispatcher

from .model_field_to_graphql_input_type import convert_model_field_to_graphql_input_type
from .type_to_graphql_input_type import convert_type_to_graphql_input_type

__all__ = [
    "convert_field_ref_to_graphql_input_type",
]


convert_field_ref_to_graphql_input_type = TypeDispatcher[FieldRef, GraphQLInputType]()


@convert_field_ref_to_graphql_input_type.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLInputType:
    annotation = parse_first_param_type(ref)
    return convert_type_to_graphql_input_type(annotation)


@convert_field_ref_to_graphql_input_type.register
def _(ref: staticmethod | classmethod) -> GraphQLInputType:
    return convert_field_ref_to_graphql_input_type(ref.__func__)  # type: ignore[arg-type]


@convert_field_ref_to_graphql_input_type.register
def _(ref: models.Field, **kwargs: Any) -> GraphQLInputType:
    return convert_model_field_to_graphql_input_type(ref)


@convert_field_ref_to_graphql_input_type.register
def _(ref: str, *, model: type[models.Model]) -> GraphQLInputType:
    model_field = parse_model_field(model=model, lookup=ref)
    return convert_model_field_to_graphql_input_type(model_field)


@convert_field_ref_to_graphql_input_type.register
def _(ref: models.Q, **kwargs: Any) -> GraphQLInputType:
    return GraphQLBoolean


@convert_field_ref_to_graphql_input_type.register
def _(ref: models.Expression, **kwargs: Any) -> GraphQLInputType:
    return convert_model_field_to_graphql_input_type(ref.output_field)


@convert_field_ref_to_graphql_input_type.register
def _(ref: models.F, *, model: type[models.Model]) -> GraphQLInputType:
    model_field = parse_model_field(model=model, lookup=ref.name)
    return convert_model_field_to_graphql_input_type(model_field)
