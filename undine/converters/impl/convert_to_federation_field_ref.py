from __future__ import annotations

import datetime
import decimal
import uuid
from types import FunctionType
from typing import Any

from graphql import GraphQLType, UndefinedType

from undine import InterfaceType, QueryType, UnionType
from undine.converters import convert_to_federation_field_ref
from undine.dataclasses import TypeRef
from undine.exceptions import MissingFederationFieldRefError
from undine.federation.federation_type import FederationField, FederationType


@convert_to_federation_field_ref.register
def _(_: UndefinedType, **kwargs: Any) -> Any:
    caller: FederationField = kwargs["caller"]
    raise MissingFederationFieldRefError(name=caller.name, cls=caller.federation_type)


@convert_to_federation_field_ref.register
def _(ref: FunctionType, **kwargs: Any) -> Any:
    return ref


@convert_to_federation_field_ref.register
def _(ref: type[QueryType], **kwargs: Any) -> Any:
    return ref


@convert_to_federation_field_ref.register
def _(ref: type[FederationType], **kwargs: Any) -> Any:
    return ref


@convert_to_federation_field_ref.register
def _(ref: type[InterfaceType], **kwargs: Any) -> Any:
    return ref


@convert_to_federation_field_ref.register
def _(ref: type[UnionType], **kwargs: Any) -> Any:
    return ref


@convert_to_federation_field_ref.register
def _(ref: GraphQLType, **kwargs: Any) -> Any:
    return ref


@convert_to_federation_field_ref.register
def _(ref: type[str], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_federation_field_ref.register
def _(ref: type[bool], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_federation_field_ref.register
def _(ref: type[int], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_federation_field_ref.register
def _(ref: type[float], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_federation_field_ref.register
def _(ref: type[decimal.Decimal], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_federation_field_ref.register
def _(ref: type[uuid.UUID], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_federation_field_ref.register
def _(ref: type[datetime.datetime], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_federation_field_ref.register
def _(ref: type[datetime.date], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_federation_field_ref.register
def _(ref: type[datetime.time], **kwargs: Any) -> Any:
    return TypeRef(value=ref)
