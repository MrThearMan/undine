from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from types import NoneType
from typing import Any, NamedTuple

import pytest
from django.db.models import (
    BigIntegerField,
    BinaryField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    FloatField,
    IntegerField,
    Q,
    Subquery,
    TextField,
    TimeField,
    UUIDField,
)
from django.db.models.functions import Now
from graphql import (
    GraphQLBoolean,
    GraphQLFloat,
    GraphQLID,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLScalarType,
    GraphQLString,
)

from example_project.app.models import Comment, Task
from tests.helpers import exact, parametrize_helper
from undine.converters import convert_to_python_type
from undine.exceptions import FunctionDispatcherError
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
    GraphQLJSON,
    GraphQLNull,
    GraphQLTime,
    GraphQLURL,
    GraphQLUUID,
)


class Params(NamedTuple):
    input_type: Any
    output_type: Any


@pytest.mark.parametrize(
    **parametrize_helper({
        "CharField": Params(
            input_type=CharField(max_length=255),
            output_type=str,
        ),
        "TextField": Params(
            input_type=TextField(),
            output_type=str,
        ),
        "BooleanField": Params(
            input_type=BooleanField(),
            output_type=bool,
        ),
        "IntegerField": Params(
            input_type=IntegerField(),
            output_type=int,
        ),
        "BigIntegerField": Params(
            input_type=BigIntegerField(),
            output_type=int,
        ),
        "FloatField": Params(
            input_type=FloatField(),
            output_type=float,
        ),
        "DecimalField": Params(
            input_type=DecimalField(),
            output_type=Decimal,
        ),
        "DateField": Params(
            input_type=DateField(),
            output_type=datetime.date,
        ),
        "DateTimeField": Params(
            input_type=DateTimeField(),
            output_type=datetime.datetime,
        ),
        "TimeField": Params(
            input_type=TimeField(),
            output_type=datetime.time,
        ),
        "DurationField": Params(
            input_type=DurationField(),
            output_type=datetime.timedelta,
        ),
        "BinaryField": Params(
            input_type=BinaryField(),
            output_type=bytes,
        ),
        "UUIDField": Params(
            input_type=UUIDField(),
            output_type=uuid.UUID,
        ),
        "ForeignKey": Params(
            input_type=Task._meta.get_field("project"),
            output_type=int,
        ),
        "OneToOneField": Params(
            input_type=Task._meta.get_field("request"),
            output_type=int,
        ),
        "ManyToManyField": Params(
            input_type=Task._meta.get_field("assignees"),
            output_type=list[int],
        ),
        "ReverseOneToOne": Params(
            input_type=Task._meta.get_field("result"),
            output_type=int,
        ),
        "ReverseForeignKey": Params(
            input_type=Task._meta.get_field("steps"),
            output_type=list[int],
        ),
        "ReverseManyToManyField": Params(
            input_type=Task._meta.get_field("reports"),
            output_type=list[int],
        ),
        "DeferredAttribute": Params(
            input_type=Task.name,
            output_type=str,
        ),
        "ForwardOneToOneDescriptor": Params(
            input_type=Task.request,
            output_type=int,
        ),
        "ForwardManyToOneDescriptor": Params(
            input_type=Task.project,
            output_type=int,
        ),
        "ReverseManyToOneDescriptor": Params(
            input_type=Task.steps,
            output_type=list[int],
        ),
        "ReverseOneToOneDescriptor": Params(
            input_type=Task.result,
            output_type=int,
        ),
        "ForwardManyToManyDescriptor": Params(
            input_type=Task.assignees,
            output_type=list[int],
        ),
        "ReverseManyToManyDescriptor": Params(
            input_type=Task.reports,
            output_type=list[int],
        ),
        "Q expression": Params(
            input_type=Q(name__exact="foo"),
            output_type=bool,
        ),
        "Expression": Params(
            input_type=Now(),
            output_type=datetime.datetime,
        ),
        "Subquery": Params(
            input_type=Subquery(Task.objects.values("id")),
            output_type=int,
        ),
        "GenericRelation": Params(
            input_type=Task._meta.get_field("comments"),
            output_type=list[int],
        ),
        "GenericRel": Params(
            input_type=Task.comments,
            output_type=list[int],
        ),
        "GenericForeignKey": Params(
            input_type=Comment._meta.get_field("target"),
            output_type=str,
        ),
        "GraphQLID": Params(
            input_type=GraphQLID,
            output_type=str,
        ),
        "GraphQLString": Params(
            input_type=GraphQLString,
            output_type=str,
        ),
        "GraphQLEmail": Params(
            input_type=GraphQLEmail,
            output_type=str,
        ),
        "GraphQLURL": Params(
            input_type=GraphQLURL,
            output_type=str,
        ),
        "GraphQLBoolean": Params(
            input_type=GraphQLBoolean,
            output_type=bool,
        ),
        "GraphQLInt": Params(
            input_type=GraphQLInt,
            output_type=int,
        ),
        "GraphQLFloat": Params(
            input_type=GraphQLFloat,
            output_type=float,
        ),
        "GraphQLDecimal": Params(
            input_type=GraphQLDecimal,
            output_type=Decimal,
        ),
        "GraphQLDate": Params(
            input_type=GraphQLDate,
            output_type=datetime.date,
        ),
        "GraphQLTime": Params(
            input_type=GraphQLTime,
            output_type=datetime.time,
        ),
        "GraphQLDateTime": Params(
            input_type=GraphQLDateTime,
            output_type=datetime.datetime,
        ),
        "GraphQLDuration": Params(
            input_type=GraphQLDuration,
            output_type=datetime.timedelta,
        ),
        "GraphQLUUID": Params(
            input_type=GraphQLUUID,
            output_type=uuid.UUID,
        ),
        "GraphQLAny": Params(
            input_type=GraphQLAny,
            output_type=Any,
        ),
        "GraphQLNull": Params(
            input_type=GraphQLNull,
            output_type=NoneType,
        ),
        "GraphQLJSON": Params(
            input_type=GraphQLJSON,
            output_type=dict,
        ),
        "GraphQLBase16": Params(
            input_type=GraphQLBase16,
            output_type=bytes,
        ),
        "GraphQLBase32": Params(
            input_type=GraphQLBase32,
            output_type=bytes,
        ),
        "GraphQLBase64": Params(
            input_type=GraphQLBase64,
            output_type=bytes,
        ),
        "GraphQLFile": Params(
            input_type=GraphQLFile,
            output_type=str,
        ),
        "GraphQLImage": Params(
            input_type=GraphQLImage,
            output_type=str,
        ),
        "GraphQLNonNull": Params(
            input_type=GraphQLNonNull(GraphQLString),
            output_type=str,  # No nullability here
        ),
        "GraphQLList": Params(
            input_type=GraphQLList(GraphQLString),
            output_type=list[str],
        ),
    }),
)
def test_convert_to_python_type(input_type, output_type) -> None:
    assert convert_to_python_type(input_type) == output_type


def test_convert_to_python_type__function__output() -> None:
    def func() -> str: ...

    assert convert_to_python_type(func, is_input=False) == str


def test_convert_to_python_type__function__input() -> None:
    def func(value: int) -> str: ...

    assert convert_to_python_type(func, is_input=True) == int


def test_convert_to_python_type__graphql_scalar__unknown() -> None:
    custom_scalar = GraphQLScalarType("Custom")

    msg = "Unknown GraphQLScalarType: 'Custom'. Cannot find matching python type."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        convert_to_python_type(custom_scalar, is_input=False)
