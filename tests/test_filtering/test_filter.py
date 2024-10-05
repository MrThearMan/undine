import pytest
from django.db import models
from django.db.models.functions import Now
from graphql import GraphQLBoolean, GraphQLList, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.helpers import MockGQLInfo
from undine import Filter, FilterSet
from undine.resolvers import FieldResolver


def test_filter__simple():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter()

    frt = MyFilter.name

    assert repr(frt) == f"<undine.filtering.Filter(ref={Task.name.field!s}, lookup_expr='exact')>"

    assert frt.ref == Task.name.field
    assert frt.lookup_expr == "exact"
    assert frt.many is False
    assert frt.distinct is False
    assert frt.required is False
    assert frt.description is None
    assert frt.deprecation_reason is None
    assert frt.extensions == {"undine_filter": frt}

    assert frt.owner == MyFilter
    assert frt.name == "name"
    assert isinstance(frt.resolver, FieldResolver)

    expr = frt.get_expression(value="foo", info=MockGQLInfo())
    assert expr == models.Q(name__exact="foo")

    field_type = frt.get_field_type()
    assert field_type == GraphQLString

    input_field = frt.as_graphql_input()
    assert input_field.type == field_type
    assert input_field.description is None
    assert input_field.deprecation_reason is None
    assert input_field.extensions == {"undine_filter": frt}


def test_filter__q_expession():
    class MyFilter(FilterSet, model=Task, auto=False):
        has_project = Filter(models.Q(project__isnull=False))

    frt = MyFilter.has_project

    assert frt.ref == models.Q(project__isnull=False)
    assert frt.lookup_expr == "exact"
    assert frt.many is False
    assert frt.distinct is False
    assert frt.required is False
    assert frt.description is None
    assert frt.deprecation_reason is None
    assert frt.extensions == {"undine_filter": frt}

    assert frt.owner == MyFilter
    assert frt.name == "has_project"
    assert isinstance(frt.resolver, FieldResolver)

    expr = frt.get_expression(value="foo", info=MockGQLInfo())
    assert expr == models.Q(project__isnull=False)

    field_type = frt.get_field_type()
    assert field_type == GraphQLBoolean

    input_field = frt.as_graphql_input()
    assert input_field.type == field_type
    assert input_field.description is None
    assert input_field.deprecation_reason is None
    assert input_field.extensions == {"undine_filter": frt}


def test_filter__function():
    class MyFilter(FilterSet, model=Task, auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> models.Q:
            """Filter tasks created in the past."""
            return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())

    frt = MyFilter.in_the_past

    assert callable(frt.ref)
    assert frt.lookup_expr == "exact"
    assert frt.many is False
    assert frt.distinct is False
    assert frt.required is False
    assert frt.description == "Filter tasks created in the past."
    assert frt.deprecation_reason is None
    assert frt.extensions == {"undine_filter": frt}

    assert frt.owner == MyFilter
    assert frt.name == "in_the_past"
    assert isinstance(frt.resolver, FieldResolver)

    expr_1 = frt.get_expression(value=True, info=MockGQLInfo())
    assert expr_1 == models.Q(created_at__lt=Now())
    expr_2 = frt.get_expression(value=False, info=MockGQLInfo())
    assert expr_2 == models.Q(created_at__gte=Now())

    field_type = frt.get_field_type()
    assert field_type == GraphQLBoolean

    input_field = frt.as_graphql_input()
    assert input_field.type == field_type
    assert input_field.description == "Filter tasks created in the past."
    assert input_field.deprecation_reason is None
    assert input_field.extensions == {"undine_filter": frt}


def test_filter__function__with_args():
    class MyFilter(FilterSet, model=Task, auto=False):
        @Filter(distinct=True)
        def in_the_past(self, *, value: bool) -> models.Q: ...

    assert MyFilter.in_the_past.distinct is True


def test_filter__deprecation_reason():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(deprecation_reason="Use something else.")

    frt = MyFilter.name

    assert frt.deprecation_reason == "Use something else."

    input_field = frt.as_graphql_input()
    assert input_field.deprecation_reason == "Use something else."


def test_filter__description():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(description="Description.")

    frt = MyFilter.name

    assert frt.description == "Description."

    input_field = frt.as_graphql_input()
    assert input_field.description == "Description."


def test_filter__required():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(required=True)

    frt = MyFilter.name

    assert frt.required is True

    field_type = frt.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert field_type.of_type == GraphQLString


def test_filter__many():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(many=True)

    frt = MyFilter.name

    assert frt.many is True

    field_type = frt.get_field_type()
    assert isinstance(field_type, GraphQLList)
    assert isinstance(field_type.of_type, GraphQLNonNull)
    assert field_type.of_type.of_type == GraphQLString


def test_filter__many_and_required():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(many=True, required=True)

    frt = MyFilter.name

    assert frt.many is True

    field_type = frt.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLList)
    assert isinstance(field_type.of_type.of_type, GraphQLNonNull)
    assert field_type.of_type.of_type.of_type == GraphQLString


@pytest.mark.parametrize("lookup_expr", ["in", "range", "IN", "RANGE"])
def test_filter__lookup_expr__assume_many(lookup_expr):
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(lookup_expr=lookup_expr)

    frt = MyFilter.name

    assert frt.many is True


def test_filter__extensions():
    class MyFilter(FilterSet, model=Task, auto=False):
        name = Filter(extensions={"foo": "bar"})

    frt = MyFilter.name

    assert frt.extensions == {"foo": "bar", "undine_filter": frt}

    input_field = frt.as_graphql_input()
    assert input_field.extensions == {"foo": "bar", "undine_filter": frt}
