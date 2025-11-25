from __future__ import annotations

import pytest
from django.db.models import Subquery, Value
from django.db.models.functions import Now
from graphql import GraphQLInt, GraphQLNonNull, GraphQLString

from example_project.app.models import Comment, Person, Project, Task
from tests.helpers import exact
from undine import (
    Calculation,
    CalculationArgument,
    DjangoExpression,
    Field,
    GQLInfo,
    InterfaceField,
    InterfaceType,
    QueryType,
)
from undine.converters import convert_to_field_resolver
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.exceptions import FunctionDispatcherError
from undine.pagination import OffsetPagination
from undine.relay import Connection
from undine.resolvers import (
    FieldFunctionResolver,
    ModelAttributeResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
)
from undine.resolvers.query import ModelGenericForeignKeyResolver, NestedConnectionResolver
from undine.typing import RelatedField


def test_convert_field_ref_to_resolver__function() -> None:
    def func() -> str: ...

    class TaskType(QueryType[Task]):
        custom = Field(func)

    resolver = convert_to_field_resolver(func, caller=TaskType.custom)

    assert isinstance(resolver, FieldFunctionResolver)

    assert resolver.func == func
    assert resolver.root_param is None
    assert resolver.info_param is None


def test_convert_field_ref_to_resolver__function__root() -> None:
    def func(root) -> str: ...

    class TaskType(QueryType[Task]):
        custom = Field(func)

    resolver = convert_to_field_resolver(func, caller=TaskType.custom)

    assert isinstance(resolver, FieldFunctionResolver)

    assert resolver.func == func
    assert resolver.root_param == "root"
    assert resolver.info_param is None


def test_convert_field_ref_to_resolver__function__self() -> None:
    def func(self) -> str: ...

    class TaskType(QueryType[Task]):
        custom = Field(func)

    resolver = convert_to_field_resolver(func, caller=TaskType.custom)

    assert isinstance(resolver, FieldFunctionResolver)

    assert resolver.func == func
    assert resolver.root_param == "self"
    assert resolver.info_param is None


def test_convert_field_ref_to_resolver__function__cls() -> None:
    def func(cls) -> str: ...

    class TaskType(QueryType[Task]):
        custom = Field(func)

    resolver = convert_to_field_resolver(func, caller=TaskType.custom)

    assert isinstance(resolver, FieldFunctionResolver)

    assert resolver.func == func
    assert resolver.root_param == "cls"
    assert resolver.info_param is None


def test_convert_field_ref_to_resolver__model_field() -> None:
    field = Task._meta.get_field("name")

    class TaskType(QueryType[Task]):
        name = Field(field)

    resolver = convert_to_field_resolver(field, caller=TaskType.name)

    assert isinstance(resolver, ModelAttributeResolver)

    assert resolver.field == TaskType.name


def test_convert_field_ref_to_resolver__single_related_field() -> None:
    field = Task._meta.get_field("project")

    class TaskType(QueryType[Task]):
        project = Field(field)

    resolver = convert_to_field_resolver(field, caller=TaskType.project)

    assert isinstance(resolver, ModelSingleRelatedFieldResolver)

    assert resolver.field == TaskType.project


def test_convert_field_ref_to_resolver__many_related_field() -> None:
    field = Task._meta.get_field("assignees")

    class TaskType(QueryType[Task]):
        assignees = Field(field)

    resolver = convert_to_field_resolver(field, caller=TaskType.assignees)

    assert isinstance(resolver, ModelManyRelatedFieldResolver)

    assert resolver.field == TaskType.assignees


def test_convert_field_ref_to_resolver__expression() -> None:
    expr = Now()

    class TaskType(QueryType[Task]):
        custom = Field(expr)

    resolver = convert_to_field_resolver(expr, caller=TaskType.custom)

    assert isinstance(resolver, ModelAttributeResolver)

    # Optimizer will annotate the expression with the field name.
    assert resolver.field == TaskType.custom


def test_convert_field_ref_to_resolver__subquery() -> None:
    sq = Subquery(Task.objects.values("id"))

    class TaskType(QueryType[Task]):
        custom = Field(sq)

    resolver = convert_to_field_resolver(sq, caller=TaskType.custom)

    assert isinstance(resolver, ModelAttributeResolver)

    # Optimizer will annotate the subquery with the field name.
    assert resolver.field == TaskType.custom


def test_convert_field_ref_to_resolver__lazy_query_type() -> None:
    field: RelatedField = Task._meta.get_field("project")

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    lazy = LazyRelation(field)
    resolver = convert_to_field_resolver(lazy, caller=TaskType.project)

    assert isinstance(resolver, NestedQueryTypeSingleResolver)

    assert resolver.field == TaskType.project


def test_convert_field_ref_to_resolver__lazy_lambda_query_type() -> None:
    class TaskType(QueryType[Task]):
        project = Field(lambda: ProjectType)

    class ProjectType(QueryType[Project]): ...

    lazy = LazyLambda(callback=lambda: ProjectType)
    resolver = convert_to_field_resolver(lazy, caller=TaskType.project)

    assert isinstance(resolver, NestedQueryTypeSingleResolver)

    assert resolver.field == TaskType.project


def test_convert_field_ref_to_resolver__lazy_query_type_union() -> None:
    field = Comment._meta.get_field("target")

    class CommentType(QueryType[Comment]):
        target = Field(field)

    lazy = LazyGenericForeignKey(field)
    resolver = convert_to_field_resolver(lazy, caller=CommentType.target)

    assert isinstance(resolver, ModelGenericForeignKeyResolver)

    assert resolver.field == CommentType.target


def test_convert_field_ref_to_resolver__generic_relation() -> None:
    field = Task._meta.get_field("comments")

    class TaskType(QueryType[Task]):
        comments = Field(field)

    resolver = convert_to_field_resolver(field, caller=TaskType.comments)

    assert isinstance(resolver, ModelManyRelatedFieldResolver)

    assert resolver.field == TaskType.comments


def test_convert_field_ref_to_resolver__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")

    class CommentType(QueryType[Comment]):
        target = Field(field)

    resolver = convert_to_field_resolver(field, caller=CommentType.target)

    assert isinstance(resolver, ModelGenericForeignKeyResolver)

    assert resolver.field == CommentType.target


def test_convert_field_ref_to_resolver__query_type() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver = convert_to_field_resolver(ProjectType, caller=TaskType.project)

    assert isinstance(resolver, NestedQueryTypeSingleResolver)

    assert resolver.field == TaskType.project


def test_convert_field_ref_to_resolver__query_type__many() -> None:
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType)

    resolver = convert_to_field_resolver(PersonType, caller=TaskType.assignees)

    assert isinstance(resolver, NestedQueryTypeManyResolver)

    assert resolver.field == TaskType.assignees


def test_convert_field_ref_to_resolver__calculated() -> None:
    class ExampleCalculation(Calculation[int | None]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    class TaskType(QueryType[Task]):
        example = Field(ExampleCalculation)

    resolver = convert_to_field_resolver(ExampleCalculation, caller=TaskType.example)

    assert isinstance(resolver, ModelAttributeResolver)


def test_convert_field_ref_to_resolver__type_ref() -> None:
    class TaskType(QueryType[Task]):
        total = Field(int)

    msg = "Must define a custom resolve for 'total' since using python type '<class 'int'>' as a reference."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        convert_to_field_resolver(TypeRef(int), caller=TaskType.total)


def test_convert_field_ref_to_resolver__graphql_type() -> None:
    class TaskType(QueryType[Task]):
        total = Field(GraphQLInt)

    msg = "Must define a custom resolve for 'total' since using GraphQLType 'Int' as a reference."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        convert_to_field_resolver(GraphQLInt, caller=TaskType.total)


def test_convert_field_ref_to_resolver__connection() -> None:
    class PersonType(QueryType[Person]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task]):
        assignees = Field(connection)

    resolver = convert_to_field_resolver(connection, caller=TaskType.assignees)

    assert isinstance(resolver, NestedConnectionResolver)


def test_convert_field_ref_to_resolver__offset_pagination() -> None:
    class PersonType(QueryType[Person]): ...

    pagination = OffsetPagination(PersonType)

    class TaskType(QueryType[Task]):
        assignees = Field(pagination)

    resolver = convert_to_field_resolver(pagination, caller=TaskType.assignees)

    assert isinstance(resolver, NestedQueryTypeManyResolver)


def test_convert_field_ref_to_resolver__interface_field() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task]):
        name = Field()

    resolver = convert_to_field_resolver(Named.name, caller=TaskType.name)

    assert isinstance(resolver, ModelAttributeResolver)
