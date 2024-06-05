from types import LambdaType

from django.db.models import Q, Subquery
from django.db.models.functions import Now

from example_project.app.models import Comment, Task
from tests.helpers import MockGQLInfo
from undine import Filter, FilterSet
from undine.converters import convert_filter_ref_to_filter_resolver
from undine.resolvers import FunctionResolver


def test_convert_filter_ref_to_filter_resolver__function():
    def func() -> str: ...

    result = convert_filter_ref_to_filter_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param is None
    assert result.info_param is None


def test_convert_filter_ref_to_filter_resolver__function__root():
    def func(root) -> str: ...

    result = convert_filter_ref_to_filter_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param == "root"
    assert result.info_param is None


def test_convert_filter_ref_to_filter_resolver__function__self():
    def func(self) -> str: ...

    result = convert_filter_ref_to_filter_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param == "self"
    assert result.info_param is None


def test_convert_filter_ref_to_filter_resolver__function__cls():
    def func(cls) -> str: ...

    result = convert_filter_ref_to_filter_resolver(func)

    assert isinstance(result, FunctionResolver)

    assert result.func == func
    assert result.root_param == "cls"
    assert result.info_param is None


def test_convert_filter_ref_to_filter_resolver__model_field():
    class TaskFilterSet(FilterSet, model=Task):
        name = Filter()

    field = Task._meta.get_field("name")
    result = convert_filter_ref_to_filter_resolver(field, caller=TaskFilterSet.name)

    assert isinstance(result, FunctionResolver)

    assert isinstance(result.func, LambdaType)
    assert result.root_param is None
    assert result.info_param is None

    assert result(root=None, info=MockGQLInfo(), value="foo") == Q(name__exact="foo")


def test_convert_filter_ref_to_filter_resolver__q_expression():
    q = Q(name__in=("foo", "bar"))

    class TaskFilterSet(FilterSet, model=Task):
        name_defined = Filter(q)

    result = convert_filter_ref_to_filter_resolver(q, caller=TaskFilterSet.name_defined)

    assert isinstance(result, FunctionResolver)

    assert isinstance(result.func, LambdaType)
    assert result.root_param is None
    assert result.info_param is None

    assert result(root=None, info=MockGQLInfo(), value=True) == q
    assert result(root=None, info=MockGQLInfo(), value=False) == ~q


def test_convert_filter_ref_to_filter_resolver__expression():
    expr = Now()

    class TaskFilterSet(FilterSet, model=Task):
        is_now = Filter(expr)

    result = convert_filter_ref_to_filter_resolver(expr, caller=TaskFilterSet.is_now)

    assert isinstance(result, FunctionResolver)

    assert isinstance(result.func, LambdaType)
    assert result.root_param is None
    assert result.info_param is None

    assert result(root=None, info=MockGQLInfo(), value=True) == Q(is_now__exact=True)


def test_convert_filter_ref_to_filter_resolver__subquery():
    sq = Subquery(Task.objects.values("id"))

    class TaskFilterSet(FilterSet, model=Task):
        first_task = Filter(sq)

    result = convert_filter_ref_to_filter_resolver(sq, caller=TaskFilterSet.first_task)

    assert isinstance(result, FunctionResolver)

    assert isinstance(result.func, LambdaType)
    assert result.root_param is None
    assert result.info_param is None

    assert result(root=None, info=MockGQLInfo(), value=1) == Q(first_task__exact=1)


def test_convert_to_field_ref__generic_relation():
    field = Task._meta.get_field("comments")

    class TaskFilterSet(FilterSet, model=Task):
        comments = Filter(field)

    result = convert_filter_ref_to_filter_resolver(field, caller=TaskFilterSet.comments)

    assert isinstance(result, FunctionResolver)

    assert isinstance(result.func, LambdaType)
    assert result.root_param is None
    assert result.info_param is None


def test_convert_to_field_ref__generic_foreign_key():
    field = Comment._meta.get_field("target")

    class CommentFilterSet(FilterSet, model=Comment):
        target = Filter(field)

    result = convert_filter_ref_to_filter_resolver(field, caller=CommentFilterSet.target)

    assert isinstance(result, FunctionResolver)

    assert isinstance(result.func, LambdaType)
    assert result.root_param is None
    assert result.info_param is None
