from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db import models

from example_project.app.models import Comment, Task
from example_project.app.types import (
    CommentNode,
    PersonNode,
    ProjectNode,
    ReportNode,
    ServiceRequestNode,
    TaskNode,
    TaskResultNode,
    TaskStepNode,
)
from undine.utils.lazy import LazyModelGQLType, LazyModelGQLTypeUnion, lazy


def test_lazy():
    foo: str = "1"

    def func():
        nonlocal foo
        foo += "1"
        return foo

    ret = lazy.create(func)

    # Accessing the original object before the lazy object
    # Original has not changed.
    assert foo == "1"

    # Accessig the lazy object should evaluate the target
    assert ret == "11"
    assert foo == "11"

    # Accessing the lazy object should not evaluate the target again
    assert ret == "11"
    assert foo == "11"


def test_lazy_model_gql_type__forward_one_to_one():
    field = Task._meta.get_field("request")
    assert isinstance(field, models.OneToOneField)

    lazy_type = LazyModelGQLType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == ServiceRequestNode


def test_lazy_model_gql_type__forward_many_to_one():
    field = Task._meta.get_field("project")
    assert isinstance(field, models.ForeignKey)

    lazy_type = LazyModelGQLType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == ProjectNode


def test_lazy_model_gql_type__forward_many_to_many():
    field = Task._meta.get_field("assignees")
    assert isinstance(field, models.ManyToManyField)

    lazy_type = LazyModelGQLType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == PersonNode


def test_lazy_model_gql_type__forward_many_to_many__self():
    field = Task._meta.get_field("related_tasks")
    assert isinstance(field, models.ManyToManyField)

    lazy_type = LazyModelGQLType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == TaskNode


def test_lazy_model_gql_type__reverse_one_to_one():
    field = Task._meta.get_field("result")
    assert isinstance(field, models.OneToOneRel)

    lazy_type = LazyModelGQLType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == TaskResultNode


def test_lazy_model_gql_type__reverse_one_to_many():
    field = Task._meta.get_field("steps")
    assert isinstance(field, models.ManyToOneRel)

    lazy_type = LazyModelGQLType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == TaskStepNode


def test_lazy_model_gql_type__reverse_many_to_many():
    field = Task._meta.get_field("reports")
    assert isinstance(field, models.ManyToManyRel)

    lazy_type = LazyModelGQLType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == ReportNode


def test_lazy_model_gql_type__generic_relation():
    field = Task._meta.get_field("comments")
    assert isinstance(field, GenericRelation)

    lazy_type = LazyModelGQLType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == CommentNode


def test_lazy_model_gql_type_union__generic_foreign_key():
    field = Comment._meta.get_field("target")
    assert isinstance(field, GenericForeignKey)

    lazy_type = LazyModelGQLTypeUnion(field=field)
    gql_type = lazy_type.get_types()
    assert isinstance(gql_type, list)
    assert len(gql_type) == 2
    assert gql_type[0] == ProjectNode
    assert gql_type[1] == TaskNode
