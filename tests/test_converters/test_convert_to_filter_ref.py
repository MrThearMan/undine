from __future__ import annotations

import pytest
from django.db.models import F, Func, Q, Subquery
from django.db.models.functions import Now

from example_project.app.models import Comment, Project, ServiceRequest, Task
from tests.helpers import mock_gql_info
from undine import Filter, FilterSet
from undine.converters import convert_to_filter_ref
from undine.dataclasses import UnionFilterRef
from undine.exceptions import UnionModelFieldDirectUsageError, UnionModelFieldMismatchError


def test_convert_to_filter_ref__str() -> None:
    class TaskFilterSet(FilterSet[Task]):
        name = Filter("name")

    field = Task._meta.get_field("name")
    assert convert_to_filter_ref("name", caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__none() -> None:
    class TaskFilterSet(FilterSet[Task]):
        name = Filter()

    field = Task._meta.get_field("name")
    assert convert_to_filter_ref(None, caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__f_expression() -> None:
    class TaskFilterSet(FilterSet[Task]):
        name = Filter(F("name"))

    field = Task._meta.get_field("name")
    assert convert_to_filter_ref(F("name"), caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__model_field() -> None:
    field = Task._meta.get_field("name")

    class TaskFilterSet(FilterSet[Task]):
        name = Filter(field)

    assert convert_to_filter_ref(field, caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__deferred_attribute() -> None:
    class TaskFilterSet(FilterSet[Task]):
        name = Filter(Task.name)

    field = Task._meta.get_field("name")
    assert convert_to_filter_ref(Task.name, caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__forward_many_to_one_descriptor() -> None:
    class TaskFilterSet(FilterSet[Task]):
        project = Filter(Task.project)

    field = Task._meta.get_field("project")
    assert convert_to_filter_ref(Task.project, caller=TaskFilterSet.project) == field


def test_convert_to_filter_ref__reverse_many_to_one_descriptor() -> None:
    class TaskFilterSet(FilterSet[Task]):
        steps = Filter(Task.steps)

    field = Task._meta.get_field("steps")
    assert convert_to_filter_ref(Task.steps, caller=TaskFilterSet.steps) == field


def test_convert_to_filter_ref__reverse_one_to_one_descriptor() -> None:
    class TaskFilterSet(FilterSet[Task]):
        result = Filter(Task.result)

    field = Task._meta.get_field("result")
    assert convert_to_filter_ref(Task.result, caller=TaskFilterSet.result) == field


def test_convert_to_filter_ref__many_to_many_descriptor__forward() -> None:
    class TaskFilterSet(FilterSet[Task]):
        assignees = Filter(Task.assignees)

    field = Task._meta.get_field("assignees")
    assert convert_to_filter_ref(Task.assignees, caller=TaskFilterSet.assignees) == field


def test_convert_to_filter_ref__many_to_many_descriptor__reverse() -> None:
    class TaskFilterSet(FilterSet[Task]):
        reports = Filter(Task.reports)

    field = Task._meta.get_field("reports")
    assert convert_to_filter_ref(Task.reports, caller=TaskFilterSet.reports) == field


def test_convert_to_filter_ref__function() -> None:
    def foo() -> str: ...

    class TaskFilterSet(FilterSet[Task]):
        custom = Filter(foo)

    assert convert_to_filter_ref(foo, caller=TaskFilterSet.custom) == foo


def test_convert_to_filter_ref__expression() -> None:
    expr = Now()

    class TaskFilterSet(FilterSet[Task]):
        custom = Filter(expr)

    assert convert_to_filter_ref(expr, caller=TaskFilterSet.custom) == expr


def test_convert_to_filter_ref__q_expression() -> None:
    q = Q(name__in=("foo", "bar"))

    class TaskFilterSet(FilterSet[Task]):
        custom = Filter(q)

    assert convert_to_filter_ref(q, caller=TaskFilterSet.custom) == q


def test_convert_to_filter_ref__subquery() -> None:
    sq = Subquery(Task.objects.values("id"))

    class TaskFilterSet(FilterSet[Task]):
        custom = Filter(sq)

    assert convert_to_filter_ref(sq, caller=TaskFilterSet.custom) == sq


def test_convert_to_filter_ref__generic_relation() -> None:
    field = Task._meta.get_field("comments")

    class TaskFilterSet(FilterSet[Task]):
        comments = Filter(field)

    assert convert_to_filter_ref(field, caller=TaskFilterSet.comments) == field


def test_convert_to_filter_ref__generic_rel() -> None:
    class TaskFilterSet(FilterSet[Task]):
        comments = Filter(Task.comments)

    field = Task._meta.get_field("comments")
    assert convert_to_filter_ref(Task.comments, caller=TaskFilterSet.comments) == field


def test_convert_to_filter_ref__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")

    class CommentFilterSet(FilterSet[Comment]):
        target = Filter(field)

    assert convert_to_filter_ref(field, caller=CommentFilterSet.target) == field


def test_convert_to_filter_ref__generic_foreign_key__direct_ref() -> None:
    class CommentFilterSet(FilterSet[Comment]):
        target = Filter(Comment.target)

    field = Comment._meta.get_field("target")
    assert convert_to_filter_ref(Comment.target, caller=CommentFilterSet.target) == field


def test_convert_to_filter_ref__str__multi_model() -> None:
    class MultiFilterSet(FilterSet[Task, Project]):
        name = Filter("name")

    result = convert_to_filter_ref("name", caller=MultiFilterSet.name)
    assert result == UnionFilterRef(ref="name", models=(Task, Project))


def test_convert_to_filter_ref__str__multi_model__type_mismatch() -> None:
    with pytest.raises(UnionModelFieldMismatchError):

        class MultiFilterSet(FilterSet[Task, ServiceRequest]):
            created_at = Filter("created_at")


def test_convert_to_filter_ref__model_field__multi_model() -> None:
    field = Task._meta.get_field("name")

    class MultiFilterSet(FilterSet[Task, Project]):
        name = Filter()

    with pytest.raises(UnionModelFieldDirectUsageError):
        convert_to_filter_ref(field, caller=MultiFilterSet.name)


def test_convert_to_filter_ref__q_expression__calls_aliases_func() -> None:
    q = Q(name="foo")

    class TaskFilterSet(FilterSet[Task]):
        custom = Filter(q)

    info = mock_gql_info()
    result = TaskFilterSet.custom.aliases_func(TaskFilterSet.custom, info, value=True)
    assert result == {"custom": q}


def test_convert_to_filter_ref__q_expression__with_existing_aliases_func() -> None:
    def existing_func(root: Filter, info, *, value: bool) -> dict:
        return {"existing": value}

    q1 = Q(name="foo")
    q2 = Q(name="bar")

    class TaskFilterSet(FilterSet[Task]):
        custom = Filter(q1)

    TaskFilterSet.custom.aliases_func = existing_func
    convert_to_filter_ref(q2, caller=TaskFilterSet.custom)

    info = mock_gql_info()
    result = TaskFilterSet.custom.aliases_func(TaskFilterSet.custom, info, value=True)
    assert "existing" in result
    assert "custom" in result


def test_convert_to_filter_ref__expression__calls_aliases_func() -> None:
    expr = Now()

    class TaskFilterSet(FilterSet[Task]):
        custom = Filter(expr)

    info = mock_gql_info()
    result = TaskFilterSet.custom.aliases_func(TaskFilterSet.custom, info, value=True)
    assert result == {"custom": expr}


def test_convert_to_filter_ref__expression__with_existing_aliases_func() -> None:
    def existing_func(root: Filter, info, *, value) -> dict:
        return {"existing": value}

    expr = Now()

    class TaskFilterSet(FilterSet[Task]):
        custom = Filter(expr)

    TaskFilterSet.custom.aliases_func = existing_func
    convert_to_filter_ref(expr, caller=TaskFilterSet.custom)

    info = mock_gql_info()
    result = TaskFilterSet.custom.aliases_func(TaskFilterSet.custom, info, value=True)
    assert "existing" in result
    assert "custom" in result


def test_convert_to_filter_ref__expression__multi_model() -> None:

    expr = Now()

    class MultiFilterSet(FilterSet[(Task, Project)]):
        custom = Filter(expr)

    result = convert_to_filter_ref(expr, caller=MultiFilterSet.custom)
    assert result is expr


def test_convert_to_filter_ref__expression__multi_model__type_mismatch() -> None:
    class FieldFunc(Func):
        function = "COALESCE"

    expr = FieldFunc(F("created_at"))

    with pytest.raises(UnionModelFieldMismatchError):

        class MultiFilterSet(FilterSet[(Task, ServiceRequest)]):
            created_at = Filter(expr)


def test_convert_to_filter_ref__generic_foreign_key__multi_model() -> None:
    field = Comment._meta.get_field("target")

    class MultiFilterSet(FilterSet[(Task, Project)]):
        name = Filter()

    with pytest.raises(UnionModelFieldDirectUsageError):
        convert_to_filter_ref(field, caller=MultiFilterSet.name)
