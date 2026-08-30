from __future__ import annotations

import datetime
import functools
import operator
import types
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, TypedDict

from django.core.files.uploadedfile import UploadedFile
from graphql import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLFloat,
    GraphQLID,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
    GraphQLUnionType,
)

from undine.converters import convert_graphql_type_to_python_type
from undine.scalars import (
    GraphQLAny,
    GraphQLBase16,
    GraphQLBase32,
    GraphQLBase64,
    GraphQLDate,
    GraphQLDateTime,
    GraphQLDecimal,
    GraphQLDuration,
    GraphQLEmail,
    GraphQLFile,
    GraphQLImage,
    GraphQLIP,
    GraphQLIPv4,
    GraphQLIPv6,
    GraphQLJSON,
    GraphQLNull,
    GraphQLTime,
    GraphQLURL,
    GraphQLUUID,
)
from undine.typing import TypeHint
from undine.utils.reflection import get_flattened_generic_params


@convert_graphql_type_to_python_type.register
def _(_: Any, **kwargs: Any) -> TypeHint | None:
    return Any


@convert_graphql_type_to_python_type.register
def _(_: GraphQLString, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLInt, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return int | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLFloat, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return float | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLBoolean, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return bool | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLID, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLAny, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return Any


@convert_graphql_type_to_python_type.register
def _(_: GraphQLBase16, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLBase32, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLBase64, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLDate, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return datetime.date | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLDateTime, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return datetime.datetime | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLTime, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return datetime.time | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLDuration, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return datetime.timedelta | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLUUID, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return uuid.UUID | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLDecimal, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return Decimal | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLEmail, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLURL, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLFile, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return UploadedFile | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLImage, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return UploadedFile | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLJSON, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return dict[str, Any] | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLIP, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLIPv4, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLIPv6, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return str | None


@convert_graphql_type_to_python_type.register
def _(_: GraphQLNull, **kwargs: Any) -> TypeHint | None:  # type: ignore[valid-type]
    return None


@convert_graphql_type_to_python_type.register
def _(ref: GraphQLNonNull, **kwargs: Any) -> TypeHint | None:
    result = convert_graphql_type_to_python_type(ref.of_type, **kwargs)
    args = get_flattened_generic_params(result)
    return functools.reduce(operator.or_, (arg for arg in args if arg is not types.NoneType))


@convert_graphql_type_to_python_type.register
def _(ref: GraphQLList, **kwargs: Any) -> TypeHint | None:
    result = convert_graphql_type_to_python_type(ref.of_type, **kwargs)
    return list.__class_getitem__(result) | None


@convert_graphql_type_to_python_type.register
def _(ref: GraphQLEnumType, **kwargs: Any) -> TypeHint | None:
    members: dict[str, Any] = {name: member.value for name, member in ref.values.items()}
    return Enum(ref.name, members) | None  # type: ignore[operator]


@convert_graphql_type_to_python_type.register
def _(ref: GraphQLUnionType, **kwargs: Any) -> TypeHint | None:
    args = (convert_graphql_type_to_python_type(arg, **kwargs) for arg in ref.types)
    args = (get_flattened_generic_params(arg)[0] for arg in args)
    return functools.reduce(operator.or_, args) | None  # type: ignore[operator]


@convert_graphql_type_to_python_type.register
def _(ref: GraphQLInterfaceType, **kwargs: Any) -> TypeHint | None:
    fields: dict[str, Any] = {
        name: convert_graphql_type_to_python_type(field.type, **kwargs) for name, field in ref.fields.items()
    }
    return TypedDict(ref.name, fields) | None  # type: ignore[operator]


@convert_graphql_type_to_python_type.register
def _(ref: GraphQLObjectType, **kwargs: Any) -> TypeHint | None:
    fields: dict[str, Any] = {
        name: convert_graphql_type_to_python_type(field.type, **kwargs) for name, field in ref.fields.items()
    }
    return TypedDict(ref.name, fields) | None  # type: ignore[operator]


@convert_graphql_type_to_python_type.register
def _(ref: GraphQLInputObjectType, **kwargs: Any) -> TypeHint | None:
    fields: dict[str, Any] = {
        name: convert_graphql_type_to_python_type(field.type, **kwargs) for name, field in ref.fields.items()
    }
    return TypedDict(ref.name, fields) | None  # type: ignore[operator]
