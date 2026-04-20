from __future__ import annotations

import pytest
from django.db.models import F, Func, Subquery
from django.db.models.functions import Now

from example_project.app.models import Comment, Project, ServiceRequest, Task
from undine import Order, OrderSet
from undine.converters import convert_to_order_ref
from undine.exceptions import UnionModelFieldDirectUsageError, UnionModelFieldMismatchError


def test_convert_to_order_ref__str() -> None:
    class TaskOrderSet(OrderSet[Task]):
        name = Order("name")

    assert convert_to_order_ref("name", caller=TaskOrderSet.name) == F("name")


def test_convert_to_order_ref__none() -> None:
    class TaskOrderSet(OrderSet[Task]):
        name = Order()

    assert convert_to_order_ref(None, caller=TaskOrderSet.name) == F("name")


def test_convert_to_order_ref__expression() -> None:
    expr = Now()

    class TaskOrderSet(OrderSet[Task]):
        custom = Order(expr)

    # Expressions will be annotated to the queryset by the optimizer.
    assert convert_to_order_ref(expr, caller=TaskOrderSet.custom) == expr


def test_convert_to_order_ref__subquery() -> None:
    sq = Subquery(Task.objects.values("id"))

    class TaskOrderSet(OrderSet[Task]):
        custom = Order(sq)

    # Subqueries will be annotated to the queryset by the optimizer.
    assert convert_to_order_ref(sq, caller=TaskOrderSet.custom) == sq


def test_convert_to_order_ref__f_expression() -> None:
    class TaskOrderSet(OrderSet[Task]):
        name = Order(F("name"))

    assert convert_to_order_ref(F("name"), caller=TaskOrderSet.name) == F("name")


def test_convert_to_order_ref__model_field() -> None:
    field = Task._meta.get_field("name")

    class TaskOrderSet(OrderSet[Task]):
        name = Order(field)

    assert convert_to_order_ref(field, caller=TaskOrderSet.name) == F("name")


def test_convert_to_order_ref__deferred_attribute() -> None:
    class TaskOrderSet(OrderSet[Task]):
        name = Order(Task.name)

    assert convert_to_order_ref(Task.name, caller=TaskOrderSet.name) == F("name")


def test_convert_to_order_ref__forward_many_to_one_descriptor() -> None:
    class TaskOrderSet(OrderSet[Task]):
        project = Order(Task.project)

    assert convert_to_order_ref(Task.project, caller=TaskOrderSet.project) == F("project")


def test_convert_to_order_ref__reverse_many_to_one_descriptor() -> None:
    class TaskOrderSet(OrderSet[Task]):
        steps = Order(Task.steps)

    assert convert_to_order_ref(Task.steps, caller=TaskOrderSet.steps) == F("steps")


def test_convert_to_order_ref__reverse_one_to_one_descriptor() -> None:
    class TaskOrderSet(OrderSet[Task]):
        result = Order(Task.result)

    assert convert_to_order_ref(Task.result, caller=TaskOrderSet.result) == F("result")


def test_convert_to_order_ref__many_to_many_descriptor__forward() -> None:
    class TaskOrderSet(OrderSet[Task]):
        assignees = Order(Task.assignees)

    assert convert_to_order_ref(Task.assignees, caller=TaskOrderSet.assignees) == F("assignees")


def test_convert_to_order_ref__many_to_many_descriptor__reverse() -> None:
    class TaskOrderSet(OrderSet[Task]):
        reports = Order(Task.reports)

    assert convert_to_order_ref(Task.reports, caller=TaskOrderSet.reports) == F("reports")


def test_convert_to_field_ref__generic_relation() -> None:
    field = Task._meta.get_field("comments")

    class TaskOrderSet(OrderSet[Task]):
        comments = Order(Task.comments)

    assert convert_to_order_ref(field, caller=TaskOrderSet.comments) == F("comments")


def test_convert_to_field_ref__generic_rel() -> None:
    class TaskOrderSet(OrderSet[Task]):
        comments = Order(Task.comments)

    assert convert_to_order_ref(Task.comments, caller=TaskOrderSet.comments) == F("comments")


def test_convert_to_field_ref__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")

    class CommentOrderSet(OrderSet[Comment]):
        target = Order(field)

    assert convert_to_order_ref(field, caller=CommentOrderSet.target) == F("target")


def test_convert_to_field_ref__generic_foreign_key__direct_ref() -> None:
    class CommentOrderSet(OrderSet[Comment]):
        target = Order(Comment.target)

    assert convert_to_order_ref(Comment.target, caller=CommentOrderSet.target) == F("target")


def test_convert_to_order_ref__str__multi_model() -> None:
    class MultiOrderSet(OrderSet[Task, Project]):
        name = Order("name")

    result = convert_to_order_ref("name", caller=MultiOrderSet.name)
    assert result == F("name")


def test_convert_to_order_ref__str__multi_model__type_mismatch() -> None:
    with pytest.raises(UnionModelFieldMismatchError):

        class MultiOrderSet(OrderSet[Task, ServiceRequest]):
            created_at = Order("created_at")


def test_convert_to_order_ref__model_field__multi_model() -> None:
    field = Task._meta.get_field("name")

    class MultiOrderSet(OrderSet[Task, Project]):
        name = Order()

    with pytest.raises(UnionModelFieldDirectUsageError):
        convert_to_order_ref(field, caller=MultiOrderSet.name)


def test_convert_to_order_ref__expression__multi_model() -> None:
    expr = Now()

    class MultiOrderSet(OrderSet[Task, Project]):
        custom = Order(expr)

    result = convert_to_order_ref(expr, caller=MultiOrderSet.custom)
    assert result is expr


def test_convert_to_order_ref__expression__multi_model__type_mismatch() -> None:
    class FieldFunc(Func):
        function = "COALESCE"

    expr = FieldFunc(F("created_at"))

    with pytest.raises(UnionModelFieldMismatchError):

        class MultiOrderSet(OrderSet[Task, ServiceRequest]):
            created_at = Order(expr)


def test_convert_to_order_ref__generic_foreign_key__multi_model() -> None:
    field = Comment._meta.get_field("target")

    class MultiOrderSet(OrderSet[Task, Project]):
        name = Order()

    with pytest.raises(UnionModelFieldDirectUsageError):
        convert_to_order_ref(field, caller=MultiOrderSet.name)
