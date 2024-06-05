from django.db.models import F, Q, Subquery
from django.db.models.functions import Now

from example_project.app.models import Comment, Task
from undine import Filter, FilterSet
from undine.converters import convert_to_filter_ref


def test_convert_to_filter_ref__str():
    class TaskFilterSet(FilterSet, model=Task):
        name = Filter("name")

    field = Task._meta.get_field("name")
    assert convert_to_filter_ref("name", caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__none():
    class TaskFilterSet(FilterSet, model=Task):
        name = Filter()

    field = Task._meta.get_field("name")
    assert convert_to_filter_ref(None, caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__f_expression():
    class TaskFilterSet(FilterSet, model=Task):
        name = Filter(F("name"))

    field = Task._meta.get_field("name")
    assert convert_to_filter_ref(F("name"), caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__model_field():
    field = Task._meta.get_field("name")

    class TaskFilterSet(FilterSet, model=Task):
        name = Filter(field)

    assert convert_to_filter_ref(field, caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__deferred_attribute():
    class TaskFilterSet(FilterSet, model=Task):
        name = Filter(Task.name)

    field = Task._meta.get_field("name")
    assert convert_to_filter_ref(Task.name, caller=TaskFilterSet.name) == field


def test_convert_to_filter_ref__forward_many_to_one_descriptor():
    class TaskFilterSet(FilterSet, model=Task):
        project = Filter(Task.project)

    field = Task._meta.get_field("project")
    assert convert_to_filter_ref(Task.project, caller=TaskFilterSet.project) == field


def test_convert_to_filter_ref__reverse_many_to_one_descriptor():
    class TaskFilterSet(FilterSet, model=Task):
        steps = Filter(Task.steps)

    field = Task._meta.get_field("steps")
    assert convert_to_filter_ref(Task.steps, caller=TaskFilterSet.steps) == field


def test_convert_to_filter_ref__reverse_one_to_one_descriptor():
    class TaskFilterSet(FilterSet, model=Task):
        result = Filter(Task.result)

    field = Task._meta.get_field("result")
    assert convert_to_filter_ref(Task.result, caller=TaskFilterSet.result) == field


def test_convert_to_filter_ref__many_to_many_descriptor__forward():
    class TaskFilterSet(FilterSet, model=Task):
        assignees = Filter(Task.assignees)

    field = Task._meta.get_field("assignees")
    assert convert_to_filter_ref(Task.assignees, caller=TaskFilterSet.assignees) == field


def test_convert_to_filter_ref__many_to_many_descriptor__reverse():
    class TaskFilterSet(FilterSet, model=Task):
        reports = Filter(Task.reports)

    field = Task._meta.get_field("reports")
    assert convert_to_filter_ref(Task.reports, caller=TaskFilterSet.reports) == field


def test_convert_to_filter_ref__function():
    def foo() -> str: ...

    class TaskFilterSet(FilterSet, model=Task):
        custom = Filter(foo)

    assert convert_to_filter_ref(foo, caller=TaskFilterSet.custom) == foo


def test_convert_to_filter_ref__expression():
    expr = Now()

    class TaskFilterSet(FilterSet, model=Task):
        custom = Filter(expr)

    assert convert_to_filter_ref(expr, caller=TaskFilterSet.custom) == expr


def test_convert_to_filter_ref__q_expression():
    q = Q(name__in=("foo", "bar"))

    class TaskFilterSet(FilterSet, model=Task):
        custom = Filter(q)

    assert convert_to_filter_ref(q, caller=TaskFilterSet.custom) == q


def test_convert_to_filter_ref__subquery():
    sq = Subquery(Task.objects.values("id"))

    class TaskFilterSet(FilterSet, model=Task):
        custom = Filter(sq)

    assert convert_to_filter_ref(sq, caller=TaskFilterSet.custom) == sq


def test_convert_to_filter_ref__generic_relation():
    field = Task._meta.get_field("comments")

    class TaskFilterSet(FilterSet, model=Task):
        comments = Filter(field)

    assert convert_to_filter_ref(field, caller=TaskFilterSet.comments) == field


def test_convert_to_filter_ref__generic_rel():
    class TaskFilterSet(FilterSet, model=Task):
        comments = Filter(Task.comments)

    field = Task._meta.get_field("comments")
    assert convert_to_filter_ref(Task.comments, caller=TaskFilterSet.comments) == field


def test_convert_to_filter_ref__generic_foreign_key():
    field = Comment._meta.get_field("target")

    class CommentFilterSet(FilterSet, model=Comment):
        target = Filter(field)

    assert convert_to_filter_ref(field, caller=CommentFilterSet.target) == field


def test_convert_to_filter_ref__generic_foreign_key__direct_ref():
    class CommentFilterSet(FilterSet, model=Comment):
        target = Filter(Comment.target)

    field = Comment._meta.get_field("target")
    assert convert_to_filter_ref(Comment.target, caller=CommentFilterSet.target) == field
