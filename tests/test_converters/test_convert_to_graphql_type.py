from __future__ import annotations

import datetime
import uuid
from contextlib import suppress
from decimal import Decimal
from enum import Enum
from typing import Any, AsyncGenerator, AsyncIterable, AsyncIterator, NamedTuple, NotRequired, Required, TypedDict

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
    EmailField,
    F,
    FileField,
    FloatField,
    GenericIPAddressField,
    ImageField,
    IntegerField,
    IPAddressField,
    JSONField,
    Model,
    Q,
    Subquery,
    Sum,
    TextChoices,
    TextField,
    TimeField,
    URLField,
    UUIDField,
    Value,
)
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
from tests.helpers import exact, mock_gql_info, parametrize_helper
from undine import Calculation, CalculationArgument, DjangoExpression, GQLInfo, MutationType, QueryType
from undine.converters import convert_to_graphql_type
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, LookupRef, MaybeManyOrNonNull, TypeRef
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
    GraphQLIP,
    GraphQLIPv4,
    GraphQLIPv6,
    GraphQLJSON,
    GraphQLTime,
    GraphQLURL,
    GraphQLUUID,
)
from undine.utils.model_fields import TextChoicesField


def test_convert_to_graphql_type__str() -> None:
    assert convert_to_graphql_type("name", model=Task) == GraphQLString


class Params(NamedTuple):
    input_type: Any
    output_type: Any


@pytest.mark.parametrize(
    **parametrize_helper({
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
        "AsyncGenerator[int, None]": Params(
            input_type=AsyncGenerator[int, None],
            output_type=GraphQLNonNull(GraphQLInt),
        ),
        "AsyncGenerator[int | Exception, None]": Params(
            input_type=AsyncGenerator[int | Exception, None],
            output_type=GraphQLNonNull(GraphQLInt),
        ),
        "AsyncGenerator[int | None, None]": Params(
            input_type=AsyncGenerator[int | None, None],
            output_type=GraphQLInt,
        ),
        "AsyncGenerator[int | Exception | None, None]": Params(
            input_type=AsyncGenerator[int | Exception | None, None],
            output_type=GraphQLInt,
        ),
        "AsyncIterator[int]": Params(
            input_type=AsyncIterator[int],
            output_type=GraphQLNonNull(GraphQLInt),
        ),
        "AsyncIterator[int | Exception]": Params(
            input_type=AsyncIterator[int | Exception],
            output_type=GraphQLNonNull(GraphQLInt),
        ),
        "AsyncIterator[int | None]": Params(
            input_type=AsyncIterator[int | None],
            output_type=GraphQLInt,
        ),
        "AsyncIterator[int | Exception | None]": Params(
            input_type=AsyncIterator[int | Exception | None],
            output_type=GraphQLInt,
        ),
        "AsyncIterable[int]": Params(
            input_type=AsyncIterable[int],
            output_type=GraphQLNonNull(GraphQLInt),
        ),
        "AsyncIterable[int | Exception]": Params(
            input_type=AsyncIterable[int | Exception],
            output_type=GraphQLNonNull(GraphQLInt),
        ),
        "AsyncIterable[int | None]": Params(
            input_type=AsyncIterable[int | None],
            output_type=GraphQLInt,
        ),
        "AsyncIterable[int | Exception | None]": Params(
            input_type=AsyncIterable[int | Exception | None],
            output_type=GraphQLInt,
        ),
    }),
)
def test_convert_to_graphql_type__type(input_type, output_type) -> None:
    assert convert_to_graphql_type(input_type) == output_type


class MyEnum(Enum):
    """Description."""

    FOO = "foo"
    BAR = "bar"


def test_convert_to_graphql_type__enum() -> None:
    result = convert_to_graphql_type(MyEnum)

    assert isinstance(result, GraphQLEnumType)
    assert result.name == "MyEnum"
    assert result.values == {
        "FOO": GraphQLEnumValue(value="FOO", description="foo"),
        "BAR": GraphQLEnumValue(value="BAR", description="bar"),
    }
    assert result.description == "Description."


class MyTextChoices(TextChoices):
    """Description."""

    FOO = "foo", "Foo"
    BAR = "bar", "Bar"


def test_convert_to_graphql_type__text_choices() -> None:
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


def test_convert_to_graphql_type__typed_dict__output() -> None:
    result = convert_to_graphql_type(MyTypedDict)

    assert isinstance(result, GraphQLObjectType)
    assert result.name == "MyTypedDict"
    assert result.fields == {
        "foo": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "bar": GraphQLField(GraphQLNonNull(GraphQLString)),
    }
    assert result.description == "Description."


def test_convert_to_graphql_type__typed_dict__input() -> None:
    result = convert_to_graphql_type(MyTypedDict, is_input=True)

    assert isinstance(result, GraphQLInputObjectType)
    assert result.name == "MyTypedDict"
    assert result.fields == {
        "foo": GraphQLInputField(GraphQLNonNull(GraphQLInt)),
        "bar": GraphQLInputField(GraphQLNonNull(GraphQLString)),
    }
    assert result.description == "Description."


class RequiredTypedDict(TypedDict, total=False):
    foo: str
    bar: str | None
    fizz: Required[str]
    buzz: Required[str | None]


def test_convert_to_graphql_type__typed_dict__required() -> None:
    result = convert_to_graphql_type(RequiredTypedDict)

    assert isinstance(result, GraphQLObjectType)
    assert result.fields == {
        "foo": GraphQLField(GraphQLString),
        "bar": GraphQLField(GraphQLString),
        "fizz": GraphQLField(GraphQLNonNull(GraphQLString)),
        "buzz": GraphQLField(GraphQLString),
    }


class NotRequiredTypedDict(TypedDict):
    foo: str
    bar: str | None
    fizz: NotRequired[str]
    buzz: NotRequired[str | None]


def test_convert_to_graphql_type__typed_dict__not_required() -> None:
    result = convert_to_graphql_type(NotRequiredTypedDict)

    assert isinstance(result, GraphQLObjectType)
    assert result.fields == {
        "foo": GraphQLField(GraphQLNonNull(GraphQLString)),
        "bar": GraphQLField(GraphQLString),
        "fizz": GraphQLField(GraphQLString),
        "buzz": GraphQLField(GraphQLString),
    }


@pytest.mark.parametrize(
    **parametrize_helper({
        "CharField": Params(
            input_type=CharField(max_length=255),
            output_type=GraphQLString,
        ),
        "TextField": Params(
            input_type=TextField(),
            output_type=GraphQLString,
        ),
        "BooleanField": Params(
            input_type=BooleanField(),
            output_type=GraphQLBoolean,
        ),
        "IntegerField": Params(
            input_type=IntegerField(),
            output_type=GraphQLInt,
        ),
        "BigIntegerField": Params(
            input_type=BigIntegerField(),
            output_type=GraphQLInt,
        ),
        "FloatField": Params(
            input_type=FloatField(),
            output_type=GraphQLFloat,
        ),
        "DecimalField": Params(
            input_type=DecimalField(),
            output_type=GraphQLDecimal,
        ),
        "DateField": Params(
            input_type=DateField(),
            output_type=GraphQLDate,
        ),
        "DateTimeField": Params(
            input_type=DateTimeField(),
            output_type=GraphQLDateTime,
        ),
        "TimeField": Params(
            input_type=TimeField(),
            output_type=GraphQLTime,
        ),
        "DurationField": Params(
            input_type=DurationField(),
            output_type=GraphQLDuration,
        ),
        "UUIDField": Params(
            input_type=UUIDField(),
            output_type=GraphQLUUID,
        ),
        "EmailField": Params(
            input_type=EmailField(),
            output_type=GraphQLEmail,
        ),
        "IPAddressField": Params(
            input_type=IPAddressField(),
            output_type=GraphQLIPv4,
        ),
        "GenericIPAddressField both": Params(
            input_type=GenericIPAddressField(),
            output_type=GraphQLIP,
        ),
        "GenericIPAddressField ipv4": Params(
            input_type=GenericIPAddressField(protocol="ipv4"),
            output_type=GraphQLIPv4,
        ),
        "GenericIPAddressField ipv6": Params(
            input_type=GenericIPAddressField(protocol="ipv6"),
            output_type=GraphQLIPv6,
        ),
        "URLField": Params(
            input_type=URLField(),
            output_type=GraphQLURL,
        ),
        "BinaryField": Params(
            input_type=BinaryField(),
            output_type=GraphQLBase64,
        ),
        "JSONField": Params(
            input_type=JSONField(),
            output_type=GraphQLJSON,
        ),
        "FileField": Params(
            input_type=FileField(),
            output_type=GraphQLFile,
        ),
        "ImageField": Params(
            input_type=ImageField(),
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
    }),
)
def test_convert_to_graphql_type__model_fields(input_type, output_type) -> None:
    assert convert_to_graphql_type(input_type) == output_type


class Role(TextChoices):
    """Role choices."""

    ADMIN = "admin", "Admin"
    USER = "user", "User"


class RoleTextChoicesFieldModel(Model):
    role: Role = CharField(choices=Role.choices, max_length=5, help_text="Role of the user.")
    actual_role: Role = TextChoicesField(choices_enum=Role)
    actual_role_help: Role = TextChoicesField(choices_enum=Role, help_text="Roles")

    class Meta:
        managed = False
        app_label = __name__


def test_convert_to_graphql_type__char_field__textchoices() -> None:
    input_type = RoleTextChoicesFieldModel._meta.get_field("role")
    result = convert_to_graphql_type(input_type)

    assert isinstance(result, GraphQLEnumType)
    assert result.name == "RoleTextChoicesFieldModelRoleChoices"
    assert result.values == {
        "admin": GraphQLEnumValue(value="admin", description="Admin"),
        "user": GraphQLEnumValue(value="user", description="User"),
    }
    assert result.description == "Role of the user."


def test_convert_to_graphql_type__text_choices_field() -> None:
    input_type = RoleTextChoicesFieldModel._meta.get_field("actual_role")
    result = convert_to_graphql_type(input_type)

    assert isinstance(result, GraphQLEnumType)
    assert result.name == "Role"
    assert result.values == {
        "admin": GraphQLEnumValue(value="admin", description="Admin"),
        "user": GraphQLEnumValue(value="user", description="User"),
    }
    assert result.description == "Role choices."


def test_convert_to_graphql_type__text_choices_field__help_text() -> None:
    input_type = RoleTextChoicesFieldModel._meta.get_field("actual_role_help")
    result = convert_to_graphql_type(input_type)

    assert result.description == "Roles"


@pytest.mark.parametrize(
    **parametrize_helper({
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
    }),
)
def test_convert_to_graphql_type__model_descriptors(input_type, output_type) -> None:
    assert convert_to_graphql_type(input_type, model=Task) == output_type


def test_convert_to_graphql_type__f_expression() -> None:
    assert convert_to_graphql_type(F("name"), model=Task) == GraphQLString


def test_convert_to_graphql_type__q_expression() -> None:
    assert convert_to_graphql_type(Q(name__exact="foo"), model=Task) == GraphQLBoolean


def test_convert_to_graphql_type__expression() -> None:
    assert convert_to_graphql_type(Now()) == GraphQLDateTime


def test_convert_to_graphql_type__subquery() -> None:
    sq = Subquery(Task.objects.values("id"))
    assert convert_to_graphql_type(sq) == GraphQLInt


def test_convert_to_graphql_type__lazy_query_type() -> None:
    class ProjectType(QueryType[Project]): ...

    field = Task._meta.get_field("project")
    lazy = LazyRelation(field=field)
    result = convert_to_graphql_type(lazy)

    assert isinstance(result, GraphQLObjectType)
    assert result.name == "ProjectType"


def test_convert_to_graphql_type__lazy_lambda_query_type() -> None:
    class ProjectType(QueryType[Project]): ...

    lazy = LazyLambda(callback=lambda: ProjectType)
    result = convert_to_graphql_type(lazy)

    assert isinstance(result, GraphQLObjectType)
    assert result.name == "ProjectType"


def test_convert_to_graphql_type__lazy_query_type_union() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]): ...

    class CommentType(QueryType[Comment]): ...

    field = Comment._meta.get_field("target")
    lazy = LazyGenericForeignKey(field=field)
    result = convert_to_graphql_type(lazy)

    assert isinstance(result, GraphQLUnionType)
    assert result.name == "CommentTarget"

    assert len(result.types) == 2
    assert result.types[0].name == "ProjectType"
    assert result.types[1].name == "TaskType"

    assert result.resolve_type(Project(), mock_gql_info(), result) == "ProjectType"
    assert result.resolve_type(Task(), mock_gql_info(), result) == "TaskType"

    msg = "Union 'CommentTarget' doesn't contain a type for model 'example_project.app.models.Comment'."
    with pytest.raises(GraphQLError, match=exact(msg)):
        result.resolve_type(Comment(), mock_gql_info(), result)


@pytest.mark.parametrize(
    **parametrize_helper({
        "type ref": Params(
            input_type=TypeRef(value=int),
            output_type=GraphQLNonNull(GraphQLInt),
        ),
        "type ref nullable": Params(
            input_type=TypeRef(value=int | None),
            output_type=GraphQLInt,
        ),
    }),
)
def test_convert_to_graphql_type__TypeRef(input_type, output_type) -> None:
    assert convert_to_graphql_type(input_type) == output_type


def test_convert_to_graphql_type__calculated() -> None:
    class ExampleCalculation(Calculation[int]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert convert_to_graphql_type(ExampleCalculation) == GraphQLNonNull(GraphQLInt)


def test_convert_to_graphql_type__calculated__nullable() -> None:
    class ExampleCalculation(Calculation[int | None]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert convert_to_graphql_type(ExampleCalculation) == GraphQLInt


def test_convert_to_graphql_type__calculated__list() -> None:
    class ExampleCalculation(Calculation[list[int]]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert convert_to_graphql_type(ExampleCalculation) == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLInt)))


@pytest.mark.parametrize(
    **parametrize_helper({
        "exact charfield": Params(
            input_type=LookupRef(CharField(), lookup="exact"),
            output_type=GraphQLString,
        ),
        "exact integerfield": Params(
            input_type=LookupRef(IntegerField(), lookup="exact"),
            output_type=GraphQLInt,
        ),
        "exact datefield": Params(
            input_type=LookupRef(DateField(), lookup="exact"),
            output_type=GraphQLDate,
        ),
        "iexact": Params(
            input_type=LookupRef(CharField(), lookup="iexact"),
            output_type=GraphQLString,
        ),
        "contains": Params(
            input_type=LookupRef(CharField(), lookup="contains"),
            output_type=GraphQLString,
        ),
        "icontains": Params(
            input_type=LookupRef(CharField(), lookup="icontains"),
            output_type=GraphQLString,
        ),
        "in charfield": Params(
            input_type=LookupRef(CharField(), lookup="in"),
            output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
        ),
        "in integerfield": Params(
            input_type=LookupRef(IntegerField(), lookup="in"),
            output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
        ),
        "in datefield": Params(
            input_type=LookupRef(DateField(), lookup="in"),
            output_type=GraphQLList(GraphQLNonNull(GraphQLDate)),
        ),
        "gt integerfield": Params(
            input_type=LookupRef(IntegerField(), lookup="gt"),
            output_type=GraphQLInt,
        ),
        "gt datefield": Params(
            input_type=LookupRef(DateField(), lookup="gt"),
            output_type=GraphQLDate,
        ),
        "gte integerfield": Params(
            input_type=LookupRef(IntegerField(), lookup="gte"),
            output_type=GraphQLInt,
        ),
        "gte datefield": Params(
            input_type=LookupRef(DateField(), lookup="gte"),
            output_type=GraphQLDate,
        ),
        "lt integerfield": Params(
            input_type=LookupRef(IntegerField(), lookup="lt"),
            output_type=GraphQLInt,
        ),
        "lt datefield": Params(
            input_type=LookupRef(DateField(), lookup="lt"),
            output_type=GraphQLDate,
        ),
        "lte integerfield": Params(
            input_type=LookupRef(IntegerField(), lookup="lte"),
            output_type=GraphQLInt,
        ),
        "lte datefield": Params(
            input_type=LookupRef(DateField(), lookup="lte"),
            output_type=GraphQLDate,
        ),
        "startswith": Params(
            input_type=LookupRef(CharField(), lookup="startswith"),
            output_type=GraphQLString,
        ),
        "istartswith": Params(
            input_type=LookupRef(CharField(), lookup="istartswith"),
            output_type=GraphQLString,
        ),
        "endswith": Params(
            input_type=LookupRef(CharField(), lookup="endswith"),
            output_type=GraphQLString,
        ),
        "iendswith": Params(
            input_type=LookupRef(CharField(), lookup="iendswith"),
            output_type=GraphQLString,
        ),
        "range integerfield": Params(
            input_type=LookupRef(IntegerField(), lookup="range"),
            output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
        ),
        "range datefield": Params(
            input_type=LookupRef(DateField(), lookup="range"),
            output_type=GraphQLList(GraphQLNonNull(GraphQLDate)),
        ),
        "is_null": Params(
            input_type=LookupRef(CharField(), lookup="isnull"),
            output_type=GraphQLBoolean,
        ),
        "regex": Params(
            input_type=LookupRef(CharField(), lookup="regex"),
            output_type=GraphQLString,
        ),
        "iregex": Params(
            input_type=LookupRef(CharField(), lookup="iregex"),
            output_type=GraphQLString,
        ),
        "date": Params(
            input_type=LookupRef(DateTimeField(), lookup="date"),
            output_type=GraphQLDate,
        ),
        "time": Params(
            input_type=LookupRef(DateTimeField(), lookup="time"),
            output_type=GraphQLTime,
        ),
        "year": Params(
            input_type=LookupRef(DateField(), lookup="year"),
            output_type=GraphQLInt,
        ),
        "month": Params(
            input_type=LookupRef(DateField(), lookup="month"),
            output_type=GraphQLInt,
        ),
        "day": Params(
            input_type=LookupRef(DateField(), lookup="day"),
            output_type=GraphQLInt,
        ),
        "week_day": Params(
            input_type=LookupRef(DateField(), lookup="week_day"),
            output_type=GraphQLInt,
        ),
        "week": Params(
            input_type=LookupRef(DateField(), lookup="week"),
            output_type=GraphQLInt,
        ),
        "hour": Params(
            input_type=LookupRef(TimeField(), lookup="hour"),
            output_type=GraphQLInt,
        ),
        "minute": Params(
            input_type=LookupRef(TimeField(), lookup="minute"),
            output_type=GraphQLInt,
        ),
        "second": Params(
            input_type=LookupRef(TimeField(), lookup="second"),
            output_type=GraphQLInt,
        ),
        "microsecond": Params(
            input_type=LookupRef(TimeField(), lookup="microsecond"),
            output_type=GraphQLInt,
        ),
        "quarter": Params(
            input_type=LookupRef(DateField(), lookup="quarter"),
            output_type=GraphQLInt,
        ),
        "iso_year": Params(
            input_type=LookupRef(DateField(), lookup="iso_year"),
            output_type=GraphQLInt,
        ),
        "iso_week_day": Params(
            input_type=LookupRef(DateField(), lookup="iso_week_day"),
            output_type=GraphQLInt,
        ),
        "unaccent": Params(
            input_type=LookupRef(CharField(), lookup="unaccent"),
            output_type=GraphQLString,
        ),
        "trigram_similar": Params(
            input_type=LookupRef(CharField(), lookup="trigram_similar"),
            output_type=GraphQLString,
        ),
        "trigram_word_similar": Params(
            input_type=LookupRef(CharField(), lookup="trigram_word_similar"),
            output_type=GraphQLString,
        ),
        "trigram_strict_word_similar": Params(
            input_type=LookupRef(CharField(), lookup="trigram_strict_word_similar"),
            output_type=GraphQLString,
        ),
    }),
)
def test_convert_to_graphql_type__lookups(input_type, output_type) -> None:
    assert convert_to_graphql_type(input_type) == output_type


def test_convert_to_graphql_type__function() -> None:
    def func() -> str: ...

    assert convert_to_graphql_type(func) == GraphQLString


def test_convert_to_graphql_type__function__is_input() -> None:
    def func(value: int) -> str: ...

    assert convert_to_graphql_type(func, is_input=True) == GraphQLInt


def test_convert_to_graphql_type__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")

    result = convert_to_graphql_type(field)

    assert result == GraphQLString


def test_convert_to_graphql_type__generic_foreign_key__is_input() -> None:
    field = Comment._meta.get_field("target")

    result = convert_to_graphql_type(field, is_input=True)

    assert isinstance(result, GraphQLInputObjectType)

    assert result.name == "CommentTargetInput"
    assert sorted(result.fields) == ["project", "task"]

    assert isinstance(result.fields["project"].type, GraphQLInputObjectType)
    assert result.fields["project"].type.name == "CommentTargetProjectInput"

    assert isinstance(result.fields["task"].type, GraphQLInputObjectType)
    assert result.fields["task"].type.name == "CommentTargetTaskInput"


def test_convert_to_graphql_type__query_type() -> None:
    class TaskType(QueryType[Task]): ...

    assert convert_to_graphql_type(TaskType) == TaskType.__output_type__()


def test_convert_to_graphql_type__mutation_type() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    assert convert_to_graphql_type(TaskCreateMutation) == TaskType.__output_type__()


def test_convert_to_graphql_type__mutation_type__is_input() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    assert convert_to_graphql_type(TaskCreateMutation, is_input=True) == TaskCreateMutation.__input_type__()


def test_convert_to_graphql_type__generated_field() -> None:
    from django.db.models import GeneratedField  # noqa: PLC0415

    field = GeneratedField(expression=Sum("number"), output_field=IntegerField(), db_persist=False)
    assert convert_to_graphql_type(field) == GraphQLInt


with suppress(ImportError):
    from django.contrib.postgres.fields import ArrayField, HStoreField

    @pytest.mark.parametrize(
        **parametrize_helper({
            "ArrayField": Params(
                input_type=ArrayField(CharField(max_length=255)),
                output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "ArrayField nullable": Params(
                input_type=ArrayField(CharField(max_length=255, null=True)),
                output_type=GraphQLList(GraphQLString),
            ),
            "HStoreField": Params(
                input_type=HStoreField(),
                output_type=GraphQLJSON,
            ),
        }),
    )
    def test_convert_to_graphql_type__postgresql_model_fields(input_type, output_type) -> None:
        assert convert_to_graphql_type(input_type) == output_type

    @pytest.mark.parametrize(
        **parametrize_helper({
            "contains arrayfield": Params(
                input_type=LookupRef(ArrayField(CharField()), lookup="contains"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "contained_by arrayfield charfield": Params(
                input_type=LookupRef(ArrayField(CharField()), lookup="contained_by"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "contained_by arrayfield integerfield": Params(
                input_type=LookupRef(ArrayField(IntegerField()), lookup="contained_by"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "overlap charfield": Params(
                input_type=LookupRef(ArrayField(CharField()), lookup="overlap"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "overlap integerfield": Params(
                input_type=LookupRef(ArrayField(IntegerField()), lookup="overlap"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "contains hstorefield": Params(
                input_type=LookupRef(HStoreField(), lookup="contains"),
                output_type=GraphQLJSON,
            ),
            "contained_by hstorefield": Params(
                input_type=LookupRef(HStoreField(), lookup="contained_by"),
                output_type=GraphQLJSON,
            ),
            "has_key": Params(
                input_type=LookupRef(HStoreField(), lookup="has_key"),
                output_type=GraphQLString,
            ),
            "has_any_keys": Params(
                input_type=LookupRef(HStoreField(), lookup="has_any_keys"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "has_keys": Params(
                input_type=LookupRef(HStoreField(), lookup="has_any_keys"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "keys": Params(
                input_type=LookupRef(HStoreField(), lookup="keys"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "values": Params(
                input_type=LookupRef(HStoreField(), lookup="values"),
                output_type=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
        }),
    )
    def test_convert_to_graphql_type__postgresql_lookups(input_type, output_type) -> None:
        assert convert_to_graphql_type(input_type) == output_type


def test_convert_to_graphql_type__maybe_many_or_non_null() -> None:
    value = MaybeManyOrNonNull(GraphQLString, many=False, nullable=True)
    assert convert_to_graphql_type(value) == GraphQLString


def test_convert_to_graphql_type__maybe_many_or_non_null__non_null() -> None:
    value = MaybeManyOrNonNull(GraphQLString, many=False, nullable=False)
    assert convert_to_graphql_type(value) == GraphQLNonNull(GraphQLString)


def test_convert_to_graphql_type__maybe_many_or_non_null__many() -> None:
    value = MaybeManyOrNonNull(GraphQLString, many=True, nullable=True)
    assert convert_to_graphql_type(value) == GraphQLList(GraphQLNonNull(GraphQLString))


def test_convert_to_graphql_type__maybe_many_or_non_null__both() -> None:
    value = MaybeManyOrNonNull(GraphQLString, many=True, nullable=False)
    assert convert_to_graphql_type(value) == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))
