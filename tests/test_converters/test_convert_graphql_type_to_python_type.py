from __future__ import annotations

import datetime
import types
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, NamedTuple

import pytest
from django.core.files.uploadedfile import UploadedFile
from graphql import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLFloat,
    GraphQLID,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
    GraphQLType,
    GraphQLUnionType,
)

from tests.helpers import parametrize_helper
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
from undine.typing import TypedDictType, TypeHint
from undine.utils.reflection import get_flattened_generic_params, get_origin_or_noop, is_subclass, is_union_origin


class Params(NamedTuple):
    value: GraphQLType
    expected: TypeHint | None


@pytest.mark.parametrize(
    **parametrize_helper({
        "GraphQLString": Params(
            value=GraphQLString,
            expected=str | None,
        ),
        "GraphQLInt": Params(
            value=GraphQLInt,
            expected=int | None,
        ),
        "GraphQLFloat": Params(
            value=GraphQLFloat,
            expected=float | None,
        ),
        "GraphQLBoolean": Params(
            value=GraphQLBoolean,
            expected=bool | None,
        ),
        "GraphQLID": Params(
            value=GraphQLID,
            expected=str | None,
        ),
        "GraphQLAny": Params(
            value=GraphQLAny,
            expected=Any,
        ),
        "GraphQLBase16": Params(
            value=GraphQLBase16,
            expected=str | None,
        ),
        "GraphQLBase32": Params(
            value=GraphQLBase32,
            expected=str | None,
        ),
        "GraphQLBase64": Params(
            value=GraphQLBase64,
            expected=str | None,
        ),
        "GraphQLDate": Params(
            value=GraphQLDate,
            expected=datetime.date | None,
        ),
        "GraphQLDateTime": Params(
            value=GraphQLDateTime,
            expected=datetime.datetime | None,
        ),
        "GraphQLDecimal": Params(
            value=GraphQLDecimal,
            expected=Decimal | None,
        ),
        "GraphQLDuration": Params(
            value=GraphQLDuration,
            expected=datetime.timedelta | None,
        ),
        "GraphQLEmail": Params(
            value=GraphQLEmail,
            expected=str | None,
        ),
        "GraphQLFile": Params(
            value=GraphQLFile,
            expected=UploadedFile | None,
        ),
        "GraphQLImage": Params(
            value=GraphQLImage,
            expected=UploadedFile | None,
        ),
        "GraphQLIP": Params(
            value=GraphQLIP,
            expected=str | None,
        ),
        "GraphQLIPv4": Params(
            value=GraphQLIPv4,
            expected=str | None,
        ),
        "GraphQLIPv6": Params(
            value=GraphQLIPv6,
            expected=str | None,
        ),
        "GraphQLJSON": Params(
            value=GraphQLJSON,
            expected=dict[str, Any] | None,
        ),
        "GraphQLNull": Params(
            value=GraphQLNull,
            expected=None,
        ),
        "GraphQLTime": Params(
            value=GraphQLTime,
            expected=datetime.time | None,
        ),
        "GraphQLURL": Params(
            value=GraphQLURL,
            expected=str | None,
        ),
        "GraphQLUUID": Params(
            value=GraphQLUUID,
            expected=uuid.UUID | None,
        ),
        "GraphQLNonNull(GraphQLString)": Params(
            value=GraphQLNonNull(GraphQLString),
            expected=str,
        ),
        "GraphQLList(GraphQLString)": Params(
            value=GraphQLList(GraphQLString),
            expected=list[str | None] | None,
        ),
        "GraphQLList(GraphQLNonNull(GraphQLInt))": Params(
            value=GraphQLList(GraphQLNonNull(GraphQLInt)),
            expected=list[int] | None,
        ),
        "GraphQLNonNull(GraphQLList(GraphQLString))": Params(
            value=GraphQLNonNull(GraphQLList(GraphQLString)),
            expected=list[str | None],
        ),
        "GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))": Params(
            value=GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString))),
            expected=list[str],
        ),
        "Any": Params(
            value=GraphQLType(),
            expected=Any,
        ),
    }),
)
def test_convert_graphql_type_to_python_type(value, expected) -> None:
    assert convert_graphql_type_to_python_type(value) == expected


def test_convert_graphql_type_to_python_type__graphql_interface() -> None:
    interface = GraphQLInterfaceType("Interface", {"field": GraphQLField(GraphQLString)})
    typ = convert_graphql_type_to_python_type(interface)

    origin = get_origin_or_noop(typ)
    args = get_flattened_generic_params(typ)

    assert is_union_origin(origin)
    assert len(args) == 2

    assert isinstance(args[0], TypedDictType)  # type: ignore[misc]
    assert args[0].__name__ == "Interface"
    assert args[0].__annotations__ == {"field": str | None}

    assert args[1] is types.NoneType


def test_convert_graphql_type_to_python_type__graphql_union() -> None:
    obj_1 = GraphQLObjectType("Obj1", {"field": GraphQLField(GraphQLString)})
    obj_2 = GraphQLObjectType("Obj2", {"field": GraphQLField(GraphQLInt)})
    union = GraphQLUnionType("Union", [obj_1, obj_2])

    typ = convert_graphql_type_to_python_type(union)

    origin = get_origin_or_noop(typ)
    args = get_flattened_generic_params(typ)

    assert is_union_origin(origin)
    assert len(args) == 3

    assert isinstance(args[0], TypedDictType)  # type: ignore[misc]
    assert args[0].__name__ == "Obj1"
    assert args[0].__annotations__ == {"field": str | None}

    assert isinstance(args[1], TypedDictType)  # type: ignore[misc]
    assert args[1].__name__ == "Obj2"
    assert args[1].__annotations__ == {"field": int | None}

    assert args[2] is types.NoneType


def test_convert_graphql_type_to_python_type__graphql_enum() -> None:
    enum = GraphQLEnumType("Enum", {"FOO": GraphQLEnumValue(1), "BAR": GraphQLEnumValue(2)})
    typ = convert_graphql_type_to_python_type(enum)

    origin = get_origin_or_noop(typ)
    args = get_flattened_generic_params(typ)

    assert is_union_origin(origin)
    assert len(args) == 2

    assert is_subclass(args[0], Enum)
    assert args[0].__name__ == "Enum"
    assert {member.name: member.value for member in args[0]} == {"FOO": 1, "BAR": 2}

    assert args[1] is types.NoneType


def test_convert_graphql_type_to_python_type__graphql_object() -> None:
    obj = GraphQLObjectType("Obj", {"field": GraphQLField(GraphQLString)})
    typ = convert_graphql_type_to_python_type(obj)

    origin = get_origin_or_noop(typ)
    args = get_flattened_generic_params(typ)

    assert is_union_origin(origin)
    assert len(args) == 2

    assert isinstance(args[0], TypedDictType)  # type: ignore[misc]
    assert args[0].__name__ == "Obj"
    assert args[0].__annotations__ == {"field": str | None}

    assert args[1] is types.NoneType


def test_convert_graphql_type_to_python_type__graphql_input_object() -> None:
    obj = GraphQLInputObjectType("Obj", {"field": GraphQLInputField(GraphQLString)})
    typ = convert_graphql_type_to_python_type(obj)

    origin = get_origin_or_noop(typ)
    args = get_flattened_generic_params(typ)

    assert is_union_origin(origin)
    assert len(args) == 2

    assert isinstance(args[0], TypedDictType)  # type: ignore[misc]
    assert args[0].__name__ == "Obj"
    assert args[0].__annotations__ == {"field": str | None}

    assert args[1] is types.NoneType
