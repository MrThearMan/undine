from __future__ import annotations

from django.db.models import Q, Subquery
from django.db.models.functions import Now

from example_project.app.models import Comment, Task
from tests.helpers import mock_gql_info
from undine import Filter, FilterSet
from undine.converters import convert_to_filter_resolver
from undine.resolvers import FilterFunctionResolver, FilterModelFieldResolver, FilterQExpressionResolver


def test_convert_filter_ref_to_filter_resolver__function() -> None:
    def func() -> str: ...

    result = convert_to_filter_resolver(func)

    assert isinstance(result, FilterFunctionResolver)

    assert result.func == func
    assert result.root_param is None
    assert result.info_param is None


def test_convert_filter_ref_to_filter_resolver__function__root() -> None:
    def func(root) -> str: ...

    result = convert_to_filter_resolver(func)

    assert isinstance(result, FilterFunctionResolver)

    assert result.func == func
    assert result.root_param == "root"
    assert result.info_param is None


def test_convert_filter_ref_to_filter_resolver__function__self() -> None:
    def func(self) -> str: ...

    result = convert_to_filter_resolver(func)

    assert isinstance(result, FilterFunctionResolver)

    assert result.func == func
    assert result.root_param == "self"
    assert result.info_param is None


def test_convert_filter_ref_to_filter_resolver__function__cls() -> None:
    def func(cls) -> str: ...

    result = convert_to_filter_resolver(func)

    assert isinstance(result, FilterFunctionResolver)

    assert result.func == func
    assert result.root_param == "cls"
    assert result.info_param is None


def test_convert_filter_ref_to_filter_resolver__model_field() -> None:
    class TaskFilterSet(FilterSet[Task]):
        name = Filter()

    field = Task._meta.get_field("name")
    result = convert_to_filter_resolver(field, caller=TaskFilterSet.name)

    assert isinstance(result, FilterModelFieldResolver)

    assert result.lookup == "name__exact"

    assert result(root=None, info=mock_gql_info(), value="foo") == Q(name__exact="foo")


def test_convert_filter_ref_to_filter_resolver__q_expression() -> None:
    q = Q(name__in=("foo", "bar"))

    class TaskFilterSet(FilterSet[Task]):
        name_defined = Filter(q)

    result = convert_to_filter_resolver(q, caller=TaskFilterSet.name_defined)

    assert isinstance(result, FilterQExpressionResolver)

    assert result.q_expression == q

    assert result(root=None, info=mock_gql_info(), value=True) == q
    assert result(root=None, info=mock_gql_info(), value=False) == ~q


def test_convert_filter_ref_to_filter_resolver__expression() -> None:
    expr = Now()

    class TaskFilterSet(FilterSet[Task]):
        is_now = Filter(expr)

    result = convert_to_filter_resolver(expr, caller=TaskFilterSet.is_now)

    assert isinstance(result, FilterModelFieldResolver)

    assert result.lookup == "is_now__exact"

    assert result(root=None, info=mock_gql_info(), value=True) == Q(is_now__exact=True)


def test_convert_filter_ref_to_filter_resolver__subquery() -> None:
    sq = Subquery(Task.objects.values("id"))

    class TaskFilterSet(FilterSet[Task]):
        first_task = Filter(sq)

    result = convert_to_filter_resolver(sq, caller=TaskFilterSet.first_task)

    assert isinstance(result, FilterModelFieldResolver)

    assert result.lookup == "first_task__exact"

    assert result(root=None, info=mock_gql_info(), value=1) == Q(first_task__exact=1)


def test_convert_to_field_ref__generic_relation() -> None:
    field = Task._meta.get_field("comments")

    class TaskFilterSet(FilterSet[Task]):
        comments = Filter(field)

    result = convert_to_filter_resolver(field, caller=TaskFilterSet.comments)

    assert isinstance(result, FilterModelFieldResolver)

    assert result.lookup == "comments__exact"


def test_convert_to_field_ref__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")

    class CommentFilterSet(FilterSet[Comment]):
        target = Filter(field)

    result = convert_to_filter_resolver(field, caller=CommentFilterSet.target)

    assert isinstance(result, FilterModelFieldResolver)

    assert result.lookup == "target__exact"
