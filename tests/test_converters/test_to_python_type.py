import datetime
import uuid
from decimal import Decimal
from typing import Any, NamedTuple

import pytest
from django.db import models
from django.db.models.functions import Now

from example_project.app.models import Comment, Task
from tests.helpers import parametrize_helper
from undine.converters import convert_to_python_type


class Params(NamedTuple):
    input_type: Any
    output_type: Any


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "CharField": Params(
                input_type=models.CharField(max_length=255),
                output_type=str,
            ),
            "TextField": Params(
                input_type=models.TextField(),
                output_type=str,
            ),
            "BooleanField": Params(
                input_type=models.BooleanField(),
                output_type=bool,
            ),
            "IntegerField": Params(
                input_type=models.IntegerField(),
                output_type=int,
            ),
            "BigIntegerField": Params(
                input_type=models.BigIntegerField(),
                output_type=int,
            ),
            "FloatField": Params(
                input_type=models.FloatField(),
                output_type=float,
            ),
            "DecimalField": Params(
                input_type=models.DecimalField(),
                output_type=Decimal,
            ),
            "DateField": Params(
                input_type=models.DateField(),
                output_type=datetime.date,
            ),
            "DateTimeField": Params(
                input_type=models.DateTimeField(),
                output_type=datetime.datetime,
            ),
            "TimeField": Params(
                input_type=models.TimeField(),
                output_type=datetime.time,
            ),
            "DurationField": Params(
                input_type=models.DurationField(),
                output_type=datetime.timedelta,
            ),
            "BinaryField": Params(
                input_type=models.BinaryField(),
                output_type=bytes,
            ),
            "UUIDField": Params(
                input_type=models.UUIDField(),
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
                input_type=models.Q(name__exact="foo"),
                output_type=bool,
            ),
            "Expression": Params(
                input_type=Now(),
                output_type=datetime.datetime,
            ),
            "Subquery": Params(
                input_type=models.Subquery(Task.objects.values("id")),
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
        },
    ),
)
def test_convert_to_python_type(input_type, output_type):
    assert convert_to_python_type(input_type) == output_type


def test_convert_to_python_type__function__output():
    def func() -> str: ...

    assert convert_to_python_type(func, is_input=False) == str


def test_convert_to_python_type__function__input():
    def func(value: int) -> str: ...

    assert convert_to_python_type(func, is_input=True) == int
