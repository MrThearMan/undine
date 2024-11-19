from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, NamedTuple, TypedDict

import pytest
from django.db import models
from django.db.models.functions import Now
from graphql import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLError,
    GraphQLField,
    GraphQLFloat,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
    GraphQLUnionType,
)

from example_project.app.models import Comment, Project, Task
from tests.helpers import MockGQLInfo, exact, parametrize_helper
from undine import MutationType, QueryType
from undine.converters import convert_to_graphql_type
from undine.scalars import (
    GraphQLAny,
    GraphQLBase64,
    GraphQLDate,
    GraphQLDateTime,
    GraphQLDecimal,
    GraphQLDuration,
    GraphQLEmail,
    GraphQLFile,
    GraphQLImage,
    GraphQLJSON,
    GraphQLTime,
    GraphQLURL,
    GraphQLUUID,
)
from undine.typing import LookupRef, TypeRef
from undine.utils.lazy import LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.utils.model_fields import TextChoicesField


def test_convert_to_graphql_type__str():
    assert convert_to_graphql_type("name", model=Task) == GraphQLString


class Params(NamedTuple):
    input_type: Any
    output_type: Any


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "str": Params(
                input_type=str,
                output_type=GraphQLString,
            ),
            "int": Params(
                input_type=int,
                output_type=GraphQLInt,
            ),
            "float": Params(
                input_type=float,
                output_type=GraphQLFloat,
            ),
            "bool": Params(
                input_type=bool,
                output_type=GraphQLBoolean,
            ),
            "decimal": Params(
                input_type=Decimal,
                output_type=GraphQLDecimal,
            ),
            "datetime": Params(
                input_type=datetime.datetime,
                output_type=GraphQLDateTime,
            ),
            "date": Params(
                input_type=datetime.date,
                output_type=GraphQLDate,
            ),
            "time": Params(
                input_type=datetime.time,
                output_type=GraphQLTime,
            ),
            "timedelta": Params(
                input_type=datetime.timedelta,
                output_type=GraphQLDuration,
            ),
            "uuid": Params(
                input_type=uuid.UUID,
                output_type=GraphQLUUID,
            ),
            "type": Params(
                input_type=type,
                output_type=GraphQLAny,
            ),
            "list": Params(
                input_type=list,
                output_type=GraphQLList(GraphQLAny),
            ),
            "list[int]": Params(
                input_type=list[int],
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "list[int | None]": Params(
                input_type=list[int | None],
                output_type=GraphQLList(GraphQLInt),
            ),
            "dict": Params(
                input_type=dict,
                output_type=GraphQLJSON,
            ),
            "dict[str, int]": Params(
                input_type=dict[str, int],
                output_type=GraphQLJSON,
            ),
        },
    ),
)
def test_convert_to_graphql_type__type(input_type, output_type):
    assert convert_to_graphql_type(input_type) == output_type


class MyEnum(Enum):
    """Description."""

    FOO = "foo"
    BAR = "bar"


def test_convert_to_graphql_type__enum():
    result = convert_to_graphql_type(MyEnum)

    assert isinstance(result, GraphQLEnumType)
    assert result.name == "MyEnum"
    assert result.values == {
        "FOO": GraphQLEnumValue(value="FOO", description="foo"),
        "BAR": GraphQLEnumValue(value="BAR", description="bar"),
    }
    assert result.description == "Description."


class MyTextChoices(models.TextChoices):
    """Description."""

    FOO = "foo", "Foo"
    BAR = "bar", "Bar"


def test_convert_to_graphql_type__text_choices():
    result = convert_to_graphql_type(MyTextChoices)

    assert isinstance(result, GraphQLEnumType)
    assert result.name == "MyTextChoices"
    assert result.values == {
        "foo": GraphQLEnumValue(value="foo", description="Foo"),
        "bar": GraphQLEnumValue(value="bar", description="Bar"),
    }
    assert result.description == "Description."


class MyTypedDict(TypedDict):
    """Description."""

    foo: int
    bar: str


def test_convert_to_graphql_type__typed_dict__output():
    result = convert_to_graphql_type(MyTypedDict)

    assert isinstance(result, GraphQLObjectType)
    assert result.name == "MyTypedDict"
    assert result.fields == {
        "foo": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "bar": GraphQLField(GraphQLNonNull(GraphQLString)),
    }
    assert result.description == "Description."


def test_convert_to_graphql_type__typed_dict__input():
    result = convert_to_graphql_type(MyTypedDict, is_input=True)

    assert isinstance(result, GraphQLInputObjectType)
    assert result.name == "MyTypedDict"
    assert result.fields == {
        "foo": GraphQLInputField(GraphQLNonNull(GraphQLInt)),
        "bar": GraphQLInputField(GraphQLNonNull(GraphQLString)),
    }
    assert result.description == "Description."


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "CharField": Params(
                input_type=models.CharField(max_length=255),
                output_type=GraphQLString,
            ),
            "TextField": Params(
                input_type=models.TextField(),
                output_type=GraphQLString,
            ),
            "BooleanField": Params(
                input_type=models.BooleanField(),
                output_type=GraphQLBoolean,
            ),
            "IntegerField": Params(
                input_type=models.IntegerField(),
                output_type=GraphQLInt,
            ),
            "BigIntegerField": Params(
                input_type=models.BigIntegerField(),
                output_type=GraphQLInt,
            ),
            "FloatField": Params(
                input_type=models.FloatField(),
                output_type=GraphQLFloat,
            ),
            "DecimalField": Params(
                input_type=models.DecimalField(),
                output_type=GraphQLDecimal,
            ),
            "DateField": Params(
                input_type=models.DateField(),
                output_type=GraphQLDate,
            ),
            "DateTimeField": Params(
                input_type=models.DateTimeField(),
                output_type=GraphQLDateTime,
            ),
            "TimeField": Params(
                input_type=models.TimeField(),
                output_type=GraphQLTime,
            ),
            "DurationField": Params(
                input_type=models.DurationField(),
                output_type=GraphQLDuration,
            ),
            "UUIDField": Params(
                input_type=models.UUIDField(),
                output_type=GraphQLUUID,
            ),
            "EmailField": Params(
                input_type=models.EmailField(),
                output_type=GraphQLEmail,
            ),
            "URLField": Params(
                input_type=models.URLField(),
                output_type=GraphQLURL,
            ),
            "BinaryField": Params(
                input_type=models.BinaryField(),
                output_type=GraphQLBase64,
            ),
            "JSONField": Params(
                input_type=models.JSONField(),
                output_type=GraphQLJSON,
            ),
            "FileField": Params(
                input_type=models.FileField(),
                output_type=GraphQLFile,
            ),
            "ImageField": Params(
                input_type=models.ImageField(),
                output_type=GraphQLImage,
            ),
            "OneToOneField": Params(
                input_type=Task._meta.get_field("request"),
                output_type=GraphQLInt,
            ),
            "ForeignKey": Params(
                input_type=Task._meta.get_field("project"),
                output_type=GraphQLInt,
            ),
            "ManyToManyField": Params(
                input_type=Task._meta.get_field("assignees"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "ReverseOneToOne": Params(
                input_type=Task._meta.get_field("result"),
                output_type=GraphQLInt,
            ),
            "ReverseForeignKey": Params(
                input_type=Task._meta.get_field("steps"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "ReverseManyToManyField": Params(
                input_type=Task._meta.get_field("reports"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "GenericRelation": Params(
                input_type=Task._meta.get_field("comments"),
                output_type=GraphQLList(GraphQLString),
            ),
            "GenericRel": Params(
                input_type=Task.comments,
                output_type=GraphQLList(GraphQLString),
            ),
            "GenericForeignKey": Params(
                input_type=Comment._meta.get_field("target"),
                output_type=GraphQLString,
            ),
        },
    ),
)
def test_convert_to_graphql_type__model_fields(input_type, output_type):
    assert convert_to_graphql_type(input_type) == output_type


class Role(models.TextChoices):
    """Role choices."""

    ADMIN = "admin", "Admin"
    USER = "user", "User"


class RoleTextChoicesFieldModel(models.Model):  # noqa: DJ008
    role: Role = models.CharField(choices=Role.choices, max_length=5, help_text="Role of the user.")
    actual_role: Role = TextChoicesField(choices_enum=Role)
    actual_role_help: Role = TextChoicesField(choices_enum=Role, help_text="Roles")

    class Meta:
        managed = False
        app_label = "tests"


def test_convert_to_graphql_type__char_field__textchoices():
    input_type = RoleTextChoicesFieldModel._meta.get_field("role")
    result = convert_to_graphql_type(input_type)

    assert isinstance(result, GraphQLEnumType)
    assert result.name == "RoleTextChoicesFieldModelRoleChoices"
    assert result.values == {
        "admin": GraphQLEnumValue(value="admin", description="Admin"),
        "user": GraphQLEnumValue(value="user", description="User"),
    }
    assert result.description == "Role of the user."


def test_convert_to_graphql_type__text_choices_field():
    input_type = RoleTextChoicesFieldModel._meta.get_field("actual_role")
    result = convert_to_graphql_type(input_type)

    assert isinstance(result, GraphQLEnumType)
    assert result.name == "Role"
    assert result.values == {
        "admin": GraphQLEnumValue(value="admin", description="Admin"),
        "user": GraphQLEnumValue(value="user", description="User"),
    }
    assert result.description == "Role choices."


def test_convert_to_graphql_type__text_choices_field__help_text():
    input_type = RoleTextChoicesFieldModel._meta.get_field("actual_role_help")
    result = convert_to_graphql_type(input_type)

    assert result.description == "Roles"


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "DeferredAttribute": Params(
                input_type=Task.name,
                output_type=GraphQLString,
            ),
            "ForwardOneToOneDescriptor": Params(
                input_type=Task.request,
                output_type=GraphQLInt,
            ),
            "ForwardManyToOneDescriptor": Params(
                input_type=Task.project,
                output_type=GraphQLInt,
            ),
            "ReverseManyToOneDescriptor": Params(
                input_type=Task.steps,
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "ReverseOneToOneDescriptor": Params(
                input_type=Task.result,
                output_type=GraphQLInt,
            ),
            "ForwardManyToManyDescriptor": Params(
                input_type=Task.assignees,
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "ReverseManyToManyDescriptor": Params(
                input_type=Task.reports,
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
        },
    ),
)
def test_convert_to_graphql_type__model_descriptors(input_type, output_type):
    assert convert_to_graphql_type(input_type, model=Task) == output_type


def test_convert_to_graphql_type__f_expression():
    assert convert_to_graphql_type(models.F("name"), model=Task) == GraphQLString


def test_convert_to_graphql_type__q_expression():
    assert convert_to_graphql_type(models.Q(name__exact="foo"), model=Task) == GraphQLBoolean


def test_convert_to_graphql_type__expression():
    assert convert_to_graphql_type(Now()) == GraphQLDateTime


def test_convert_to_graphql_type__subquery():
    sq = models.Subquery(Task.objects.values("id"))
    assert convert_to_graphql_type(sq) == GraphQLInt


def test_convert_to_graphql_type__lazy_query_type():
    class ProjectType(QueryType, model=Project): ...

    field = Task._meta.get_field("project")
    lazy = LazyQueryType(field=field)
    result = convert_to_graphql_type(lazy)

    assert isinstance(result, GraphQLObjectType)
    assert result.name == "ProjectType"


def test_convert_to_graphql_type__lazy_lambda_query_type():
    class ProjectType(QueryType, model=Project): ...

    lazy = LazyLambdaQueryType(callback=lambda: ProjectType)
    result = convert_to_graphql_type(lazy)

    assert isinstance(result, GraphQLObjectType)
    assert result.name == "ProjectType"


def test_convert_to_graphql_type__lazy_query_type_union():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task): ...

    class CommentType(QueryType, model=Comment): ...

    field = Comment._meta.get_field("target")
    lazy = LazyQueryTypeUnion(field=field)
    result = convert_to_graphql_type(lazy)

    assert isinstance(result, GraphQLUnionType)
    assert result.name == "CommentTarget"

    assert len(result.types) == 2
    assert result.types[0].name == "ProjectType"
    assert result.types[1].name == "TaskType"

    assert result.resolve_type(Project(), MockGQLInfo(), result) == "ProjectType"
    assert result.resolve_type(Task(), MockGQLInfo(), result) == "TaskType"

    msg = "Union 'CommentTarget' doesn't contain a 'GraphQLObjectType' for model 'example_project.app.models.Comment'."
    with pytest.raises(GraphQLError, match=exact(msg)):
        result.resolve_type(Comment(), MockGQLInfo(), result)


def test_convert_to_graphql_type__type_ref():
    assert convert_to_graphql_type(TypeRef(int)) == GraphQLInt


def test_convert_to_graphql_type__lookup_ref():
    field = Task._meta.get_field("name")
    assert convert_to_graphql_type(LookupRef(field, lookup="exact")) == GraphQLString


def test_convert_to_graphql_type__function():
    def func() -> str: ...

    assert convert_to_graphql_type(func) == GraphQLString


def test_convert_to_graphql_type__function__is_input():
    def func(value: int) -> str: ...

    assert convert_to_graphql_type(func, is_input=True) == GraphQLInt


def test_convert_to_graphql_type__generic_foreign_key__is_input():
    field = Comment._meta.get_field("target")

    result = convert_to_graphql_type(field, is_input=True)

    assert isinstance(result, GraphQLInputObjectType)

    assert result.name == "CommentTargetInput"
    assert sorted(result.fields) == ["pk", "typename"]

    assert isinstance(result.fields["pk"].type, GraphQLNonNull)
    assert result.fields["pk"].type.of_type == GraphQLString

    assert isinstance(result.fields["typename"].type, GraphQLNonNull)
    assert isinstance(result.fields["typename"].type.of_type, GraphQLEnumType)
    assert result.fields["typename"].type.of_type.name == "CommentTargetChoices"

    assert result.fields["typename"].type.of_type.values == {
        "PROJECT": GraphQLEnumValue(value="PROJECT", description="Project"),
        "TASK": GraphQLEnumValue(value="TASK", description="Task"),
    }


def test_convert_to_graphql_type__query_type():
    class TaskType(QueryType, model=Task): ...

    assert convert_to_graphql_type(TaskType) == TaskType.__output_type__()


def test_convert_to_graphql_type__mutation_type():
    class TaskType(QueryType, model=Task): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    assert convert_to_graphql_type(TaskCreateMutation) == TaskType.__output_type__()


def test_convert_to_graphql_type__mutation_type__is_input():
    class TaskType(QueryType, model=Task): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    assert convert_to_graphql_type(TaskCreateMutation, is_input=True) == TaskCreateMutation.__input_type__()
