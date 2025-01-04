from typing import TypedDict

from django.db.models import Subquery
from django.db.models.functions import Now

from example_project.app.models import Comment, Person, Project, Task
from undine import Field, QueryType
from undine.converters import convert_field_ref_to_resolver
from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.resolvers import (
    FunctionResolver,
    ModelFieldResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
)
from undine.typing import RelatedField


def test_convert_field_ref_to_resolver__function():
    def func() -> str: ...

    class TaskType(QueryType, model=Task):
        custom = Field(func)

    resolver = convert_field_ref_to_resolver(func, caller=TaskType.custom)

    assert isinstance(resolver, FunctionResolver)

    assert resolver.func == func
    assert resolver.root_param is None
    assert resolver.info_param is None


def test_convert_field_ref_to_resolver__function__root():
    def func(root) -> str: ...

    class TaskType(QueryType, model=Task):
        custom = Field(func)

    resolver = convert_field_ref_to_resolver(func, caller=TaskType.custom)

    assert isinstance(resolver, FunctionResolver)

    assert resolver.func == func
    assert resolver.root_param == "root"
    assert resolver.info_param is None


def test_convert_field_ref_to_resolver__function__self():
    def func(self) -> str: ...

    class TaskType(QueryType, model=Task):
        custom = Field(func)

    resolver = convert_field_ref_to_resolver(func, caller=TaskType.custom)

    assert isinstance(resolver, FunctionResolver)

    assert resolver.func == func
    assert resolver.root_param == "self"
    assert resolver.info_param is None


def test_convert_field_ref_to_resolver__function__cls():
    def func(cls) -> str: ...

    class TaskType(QueryType, model=Task):
        custom = Field(func)

    resolver = convert_field_ref_to_resolver(func, caller=TaskType.custom)

    assert isinstance(resolver, FunctionResolver)

    assert resolver.func == func
    assert resolver.root_param == "cls"
    assert resolver.info_param is None


def test_convert_field_ref_to_resolver__model_field():
    field = Task._meta.get_field("name")

    class TaskType(QueryType, model=Task):
        name = Field(field)

    resolver = convert_field_ref_to_resolver(field, caller=TaskType.name)

    assert isinstance(resolver, ModelFieldResolver)

    assert resolver.field == TaskType.name


def test_convert_field_ref_to_resolver__single_related_field():
    field = Task._meta.get_field("project")

    class TaskType(QueryType, model=Task):
        project = Field(field)

    resolver = convert_field_ref_to_resolver(field, caller=TaskType.project)

    assert isinstance(resolver, ModelSingleRelatedFieldResolver)

    assert resolver.field == TaskType.project


def test_convert_field_ref_to_resolver__many_related_field():
    field = Task._meta.get_field("assignees")

    class TaskType(QueryType, model=Task):
        assignees = Field(field)

    resolver = convert_field_ref_to_resolver(field, caller=TaskType.assignees)

    assert isinstance(resolver, ModelManyRelatedFieldResolver)

    assert resolver.field == TaskType.assignees


def test_convert_field_ref_to_resolver__expression():
    expr = Now()

    class TaskType(QueryType, model=Task):
        custom = Field(expr)

    resolver = convert_field_ref_to_resolver(expr, caller=TaskType.custom)

    assert isinstance(resolver, ModelFieldResolver)

    # Optimizer will annotate the expression with the field name.
    assert resolver.field == TaskType.custom


def test_convert_field_ref_to_resolver__subquery():
    sq = Subquery(Task.objects.values("id"))

    class TaskType(QueryType, model=Task):
        custom = Field(sq)

    resolver = convert_field_ref_to_resolver(sq, caller=TaskType.custom)

    assert isinstance(resolver, ModelFieldResolver)

    # Optimizer will annotate the subquery with the field name.
    assert resolver.field == TaskType.custom


def test_convert_field_ref_to_resolver__lazy_query_type():
    field: RelatedField = Task._meta.get_field("project")  # type: ignore[attr-defined]

    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

    lazy = LazyQueryType(field)
    resolver = convert_field_ref_to_resolver(lazy, caller=TaskType.project)

    assert isinstance(resolver, NestedQueryTypeSingleResolver)

    assert resolver.field == TaskType.project


def test_convert_field_ref_to_resolver__lazy_lambda_query_type():
    class TaskType(QueryType, model=Task):
        project = Field(lambda: ProjectType)

    class ProjectType(QueryType, model=Project): ...

    lazy = LazyLambdaQueryType(callback=lambda: ProjectType)
    resolver = convert_field_ref_to_resolver(lazy, caller=TaskType.project)

    assert isinstance(resolver, NestedQueryTypeSingleResolver)

    assert resolver.field == TaskType.project


def test_convert_field_ref_to_resolver__lazy_query_type_union():
    field = Comment._meta.get_field("target")

    class CommentType(QueryType, model=Comment):
        target = Field(field)

    lazy = LazyQueryTypeUnion(field)
    resolver = convert_field_ref_to_resolver(lazy, caller=CommentType.target)

    assert isinstance(resolver, ModelSingleRelatedFieldResolver)

    assert resolver.field == CommentType.target


def test_convert_field_ref_to_resolver__generic_relation():
    field = Task._meta.get_field("comments")

    class TaskType(QueryType, model=Task):
        comments = Field(field)

    resolver = convert_field_ref_to_resolver(field, caller=TaskType.comments)

    assert isinstance(resolver, ModelManyRelatedFieldResolver)

    assert resolver.field == TaskType.comments


def test_convert_field_ref_to_resolver__generic_foreign_key():
    field = Comment._meta.get_field("target")

    class CommentType(QueryType, model=Comment):
        target = Field(field)

    resolver = convert_field_ref_to_resolver(field, caller=CommentType.target)

    assert isinstance(resolver, ModelSingleRelatedFieldResolver)

    assert resolver.field == CommentType.target


def test_convert_field_ref_to_resolver__query_type():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

    resolver = convert_field_ref_to_resolver(ProjectType, caller=TaskType.project)

    assert isinstance(resolver, NestedQueryTypeSingleResolver)

    assert resolver.field == TaskType.project


def test_convert_field_ref_to_resolver__query_type__many():
    class PersonType(QueryType, model=Person): ...

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType)

    resolver = convert_field_ref_to_resolver(PersonType, caller=TaskType.assignees)

    assert isinstance(resolver, NestedQueryTypeManyResolver)

    assert resolver.field == TaskType.assignees


def test_convert_field_ref_to_resolver__calculated():
    class Arguments(TypedDict):
        value: int

    calc = Calculated(Arguments, returns=int)

    class TaskType(QueryType, model=Task):
        calculated = Field(calc)

    resolver = convert_field_ref_to_resolver(calc, caller=TaskType.calculated)

    assert isinstance(resolver, ModelFieldResolver)
