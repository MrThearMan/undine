import pytest
from django.db import models
from django.db.models.functions import Now
from graphql import GraphQLBoolean, GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from tests.helpers import MockGQLInfo
from undine import Filter, FilterSet
from undine.resolvers import FunctionResolver


def test_filter__repr():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter()

    field = Task._meta.get_field("name")
    assert repr(MyFilter.name) == f"<undine.filtering.Filter(ref={field}, lookup_expr='exact')>"


def test_filter__attributes():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter()

    assert MyFilter.name.ref == Task._meta.get_field("name")
    assert MyFilter.name.lookup_expr == "exact"
    assert MyFilter.name.many is False
    assert MyFilter.name.distinct is False
    assert MyFilter.name.required is False
    assert MyFilter.name.description is None
    assert MyFilter.name.deprecation_reason is None
    assert MyFilter.name.extensions == {"undine_filter": MyFilter.name}
    assert MyFilter.name.owner == MyFilter
    assert MyFilter.name.name == "name"
    assert isinstance(MyFilter.name.resolver, FunctionResolver)


def test_filter__get_expression():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter()

    expr = MyFilter.name.get_expression(value="foo", info=MockGQLInfo())
    assert expr == models.Q(name__exact="foo")


def test_filter__get_field_type():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter()

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLString


def test_filter__as_graphql_input():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter()

    input_field = MyFilter.name.as_graphql_input()
    assert input_field.type == GraphQLString
    assert input_field.description is None
    assert input_field.deprecation_reason is None
    assert input_field.extensions == {"undine_filter": MyFilter.name}


def test_filter__q_expession():
    q = models.Q(project__isnull=False)

    class MyFilter(FilterSet, model=Task, auto=False):
        has_project = Filter(q)

    assert MyFilter.has_project.ref == q
    assert MyFilter.has_project.lookup_expr == "exact"

    expr = MyFilter.has_project.get_expression(value="foo", info=MockGQLInfo())
    assert expr == q

    field_type = MyFilter.has_project.get_field_type()
    assert field_type == GraphQLBoolean

    input_field = MyFilter.has_project.as_graphql_input()
    assert input_field.type == GraphQLBoolean


def test_filter__expression():
    ex = models.Count("assignees")

    class MyFilter(FilterSet, model=Task, auto=False):
        assignee_count = Filter(ex, lookup_expr="lt")

    assert MyFilter.assignee_count.ref == ex
    assert MyFilter.assignee_count.lookup_expr == "lt"

    expr = MyFilter.assignee_count.get_expression(value=1, info=MockGQLInfo())
    assert expr == models.Q(assignee_count__lt=1)

    field_type = MyFilter.assignee_count.get_field_type()
    assert field_type == GraphQLInt

    input_field = MyFilter.assignee_count.as_graphql_input()
    assert input_field.type == GraphQLInt


def test_filter__subquery():
    sq = models.Subquery(queryset=Project.objects.values("id"))

    class MyFilter(FilterSet, model=Task, auto=False):
        project_id = Filter(sq)

    assert MyFilter.project_id.ref == sq
    assert MyFilter.project_id.lookup_expr == "exact"

    expr = MyFilter.project_id.get_expression(value=1, info=MockGQLInfo())
    assert expr == models.Q(project_id__exact=1)

    field_type = MyFilter.project_id.get_field_type()
    assert field_type == GraphQLInt

    input_field = MyFilter.project_id.as_graphql_input()
    assert input_field.type == GraphQLInt


def test_filter__function__repr():
    class MyFilter(FilterSet, model=Task, auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> models.Q:
            return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())

    assert repr(MyFilter.in_the_past) == (
        f"<undine.filtering.Filter(ref={MyFilter.in_the_past.ref}, lookup_expr='exact')>"
    )


def test_filter__function__attributes():
    class MyFilter(FilterSet, model=Task, auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> models.Q:
            """Filter tasks created in the past."""
            return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())

    assert callable(MyFilter.in_the_past.ref)
    assert MyFilter.in_the_past.lookup_expr == "exact"
    assert MyFilter.in_the_past.many is False
    assert MyFilter.in_the_past.distinct is False
    assert MyFilter.in_the_past.required is False
    assert MyFilter.in_the_past.description == "Filter tasks created in the past."
    assert MyFilter.in_the_past.deprecation_reason is None
    assert MyFilter.in_the_past.extensions == {"undine_filter": MyFilter.in_the_past}
    assert MyFilter.in_the_past.owner == MyFilter
    assert MyFilter.in_the_past.name == "in_the_past"
    assert isinstance(MyFilter.in_the_past.resolver, FunctionResolver)


def test_filter__function__get_expression():
    class MyFilter(FilterSet, model=Task, auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> models.Q:
            return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())

    expr_1 = MyFilter.in_the_past.get_expression(value=True, info=MockGQLInfo())
    assert expr_1 == models.Q(created_at__lt=Now())

    expr_2 = MyFilter.in_the_past.get_expression(value=False, info=MockGQLInfo())
    assert expr_2 == models.Q(created_at__gte=Now())


def test_filter__function__get_field_type():
    class MyFilter(FilterSet, model=Task, auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> models.Q:
            return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())

    field_type = MyFilter.in_the_past.get_field_type()
    assert field_type == GraphQLBoolean


def test_filter__function__as_graphql_input():
    class MyFilter(FilterSet, model=Task, auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> models.Q:
            """Filter tasks created in the past."""
            return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())

    input_field = MyFilter.in_the_past.as_graphql_input()
    assert input_field.type == GraphQLBoolean
    assert input_field.description == "Filter tasks created in the past."
    assert input_field.deprecation_reason is None
    assert input_field.extensions == {"undine_filter": MyFilter.in_the_past}


def test_filter__function__with_args():
    class MyFilter(FilterSet, model=Task, auto=False):
        @Filter(distinct=True)
        def in_the_past(self, *, value: bool) -> models.Q: ...

    assert MyFilter.in_the_past.distinct is True


def test_filter__deprecation_reason():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(deprecation_reason="Use something else.")

    assert MyFilter.name.deprecation_reason == "Use something else."

    input_field = MyFilter.name.as_graphql_input()
    assert input_field.deprecation_reason == "Use something else."


def test_filter__description():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(description="Description.")

    assert MyFilter.name.description == "Description."

    input_field = MyFilter.name.as_graphql_input()
    assert input_field.description == "Description."


def test_filter__required():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(required=True)

    assert MyFilter.name.required is True

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLString)


def test_filter__many():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(many=True)

    assert MyFilter.name.many is True

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLList(GraphQLNonNull(GraphQLString))


def test_filter__many_and_required():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(many=True, required=True)

    assert MyFilter.name.many is True

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


@pytest.mark.parametrize("lookup_expr", ["in", "range", "IN", "RANGE"])
def test_filter__lookup_expr__assume_many(lookup_expr):
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(lookup_expr=lookup_expr)

    assert MyFilter.name.many is True


def test_filter__extensions():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(extensions={"foo": "bar"})

    assert MyFilter.name.extensions == {"foo": "bar", "undine_filter": MyFilter.name}

    input_field = MyFilter.name.as_graphql_input()
    assert input_field.extensions == {"foo": "bar", "undine_filter": MyFilter.name}
