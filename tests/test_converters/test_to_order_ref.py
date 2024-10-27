from django.db import models
from django.db.models.functions import Now

from example_project.app.models import Comment, Task
from undine import Order, OrderSet
from undine.converters import convert_to_order_ref


def test_convert_to_order_ref__str():
    class TaskOrderSet(OrderSet, model=Task):
        name = Order("name")

    assert convert_to_order_ref("name", caller=TaskOrderSet.name) == models.F("name")


def test_convert_to_order_ref__none():
    class TaskOrderSet(OrderSet, model=Task):
        name = Order()

    assert convert_to_order_ref(None, caller=TaskOrderSet.name) == models.F("name")


def test_convert_to_order_ref__expression():
    expr = Now()

    class TaskOrderSet(OrderSet, model=Task):
        custom = Order(expr)

    # Expressions will be annotated to the queryset by the optimizer.
    assert convert_to_order_ref(expr, caller=TaskOrderSet.custom) == expr


def test_convert_to_order_ref__subquery():
    sq = models.Subquery(Task.objects.values("id"))

    class TaskOrderSet(OrderSet, model=Task):
        custom = Order(sq)

    # Subqueries will be annotated to the queryset by the optimizer.
    assert convert_to_order_ref(sq, caller=TaskOrderSet.custom) == sq


def test_convert_to_order_ref__f_expression():
    class TaskOrderSet(OrderSet, model=Task):
        name = Order(models.F("name"))

    assert convert_to_order_ref(models.F("name"), caller=TaskOrderSet.name) == models.F("name")


def test_convert_to_order_ref__model_field():
    field = Task._meta.get_field("name")

    class TaskOrderSet(OrderSet, model=Task):
        name = Order(field)

    assert convert_to_order_ref(field, caller=TaskOrderSet.name) == models.F("name")


def test_convert_to_order_ref__deferred_attribute():
    class TaskOrderSet(OrderSet, model=Task):
        name = Order(Task.name)

    assert convert_to_order_ref(Task.name, caller=TaskOrderSet.name) == models.F("name")


def test_convert_to_order_ref__forward_many_to_one_descriptor():
    class TaskOrderSet(OrderSet, model=Task):
        project = Order(Task.project)

    assert convert_to_order_ref(Task.project, caller=TaskOrderSet.project) == models.F("project")


def test_convert_to_order_ref__reverse_many_to_one_descriptor():
    class TaskOrderSet(OrderSet, model=Task):
        steps = Order(Task.steps)

    assert convert_to_order_ref(Task.steps, caller=TaskOrderSet.steps) == models.F("steps")


def test_convert_to_order_ref__reverse_one_to_one_descriptor():
    class TaskOrderSet(OrderSet, model=Task):
        result = Order(Task.result)

    assert convert_to_order_ref(Task.result, caller=TaskOrderSet.result) == models.F("result")


def test_convert_to_order_ref__many_to_many_descriptor__forward():
    class TaskOrderSet(OrderSet, model=Task):
        assignees = Order(Task.assignees)

    assert convert_to_order_ref(Task.assignees, caller=TaskOrderSet.assignees) == models.F("assignees")


def test_convert_to_order_ref__many_to_many_descriptor__reverse():
    class TaskOrderSet(OrderSet, model=Task):
        reports = Order(Task.reports)

    assert convert_to_order_ref(Task.reports, caller=TaskOrderSet.reports) == models.F("reports")


def test_convert_to_field_ref__generic_relation():
    field = Task._meta.get_field("comments")

    class TaskOrderSet(OrderSet, model=Task):
        comments = Order(Task.comments)

    assert convert_to_order_ref(field, caller=TaskOrderSet.comments) == models.F("comments")


def test_convert_to_field_ref__generic_rel():
    class TaskOrderSet(OrderSet, model=Task):
        comments = Order(Task.comments)

    assert convert_to_order_ref(Task.comments, caller=TaskOrderSet.comments) == models.F("comments")


def test_convert_to_field_ref__generic_foreign_key():
    field = Comment._meta.get_field("target")

    class CommentOrderSet(OrderSet, model=Comment):
        target = Order(field)

    assert convert_to_order_ref(field, caller=CommentOrderSet.target) == models.F("target")


def test_convert_to_field_ref__generic_foreign_key__direct_ref():
    class CommentOrderSet(OrderSet, model=Comment):
        target = Order(Comment.target)

    assert convert_to_order_ref(Comment.target, caller=CommentOrderSet.target) == models.F("target")
