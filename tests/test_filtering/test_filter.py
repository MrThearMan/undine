from __future__ import annotations

import operator

import pytest
from django.db.models import Count, Q, Subquery
from django.db.models.functions import Now
from graphql import DirectiveLocation, GraphQLBoolean, GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from tests.helpers import mock_gql_info
from undine import Filter, FilterSet
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError
from undine.filtering import FilterSetMeta
from undine.resolvers import FilterFunctionResolver, FilterModelFieldResolver
from undine.typing import ManyMatch


def test_filter__repr() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter()

    assert repr(MyFilter.name) == (
        "<undine.filtering.Filter(ref=<django.db.models.fields.CharField: name>, lookup='exact')>"
    )


def test_filter__str() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter()

    assert str(MyFilter.name) == "name: String"


def test_filter__attributes() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter()

    assert MyFilter.name.ref == Task._meta.get_field("name")
    assert MyFilter.name.lookup == "exact"
    assert MyFilter.name.many is False
    assert MyFilter.name.distinct is False
    assert MyFilter.name.required is False
    assert MyFilter.name.description is None
    assert MyFilter.name.deprecation_reason is None
    assert MyFilter.name.directives == []
    assert MyFilter.name.schema_name == "name"
    assert MyFilter.name.extensions == {"undine_filter": MyFilter.name}

    assert MyFilter.name.filterset == MyFilter
    assert MyFilter.name.name == "name"

    assert isinstance(MyFilter.name.resolver, FilterModelFieldResolver)


def test_filter__get_expression() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter()

    expr = MyFilter.name.get_expression(value="foo", info=mock_gql_info())
    assert expr == Q(name__exact="foo")


def test_filter__get_field_type() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter()

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLString


def test_filter__as_graphql_input() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter()

    input_field = MyFilter.name.as_graphql_input_field()
    assert input_field.type == GraphQLString
    assert input_field.description is None
    assert input_field.deprecation_reason is None
    assert input_field.extensions == {"undine_filter": MyFilter.name}


def test_filter__q_expression() -> None:
    q = Q(project__isnull=False)

    class MyFilter(FilterSet[Task], auto=False):
        has_project = Filter(q)

    assert MyFilter.has_project.ref == q
    assert MyFilter.has_project.lookup == "exact"

    expr = MyFilter.has_project.get_expression(value="foo", info=mock_gql_info())
    assert expr == q

    field_type = MyFilter.has_project.get_field_type()
    assert field_type == GraphQLBoolean

    input_field = MyFilter.has_project.as_graphql_input_field()
    assert input_field.type == GraphQLBoolean


def test_filter__expression() -> None:
    ex = Count("assignees")

    class MyFilter(FilterSet[Task], auto=False):
        assignee_count = Filter(ex, lookup="lt")

    assert MyFilter.assignee_count.ref == ex
    assert MyFilter.assignee_count.lookup == "lt"

    expr = MyFilter.assignee_count.get_expression(value=1, info=mock_gql_info())
    assert expr == Q(assignee_count__lt=1)

    field_type = MyFilter.assignee_count.get_field_type()
    assert field_type == GraphQLInt

    input_field = MyFilter.assignee_count.as_graphql_input_field()
    assert input_field.type == GraphQLInt


def test_filter__subquery() -> None:
    sq = Subquery(queryset=Project.objects.values("id"))

    class MyFilter(FilterSet[Task], auto=False):
        project_id = Filter(sq)

    assert MyFilter.project_id.ref == sq
    assert MyFilter.project_id.lookup == "exact"

    expr = MyFilter.project_id.get_expression(value=1, info=mock_gql_info())
    assert expr == Q(project_id__exact=1)

    field_type = MyFilter.project_id.get_field_type()
    assert field_type == GraphQLInt

    input_field = MyFilter.project_id.as_graphql_input_field()
    assert input_field.type == GraphQLInt


def test_filter__function__repr() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        @Filter
        def foo(self, *, value: bool) -> Q: ...

    assert repr(MyFilter.foo) == f"<undine.filtering.Filter(ref={MyFilter.foo.ref}, lookup='exact')>"


def test_filter__function__attributes() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> Q:
            """Filter tasks created in the past."""

    assert callable(MyFilter.in_the_past.ref)
    assert MyFilter.in_the_past.lookup == "exact"
    assert MyFilter.in_the_past.many is False
    assert MyFilter.in_the_past.match == ManyMatch.any
    assert MyFilter.in_the_past.distinct is False
    assert MyFilter.in_the_past.required is False
    assert MyFilter.in_the_past.description == "Filter tasks created in the past."
    assert MyFilter.in_the_past.deprecation_reason is None
    assert MyFilter.in_the_past.extensions == {"undine_filter": MyFilter.in_the_past}
    assert MyFilter.in_the_past.filterset == MyFilter
    assert MyFilter.in_the_past.name == "in_the_past"
    assert isinstance(MyFilter.in_the_past.resolver, FilterFunctionResolver)


def test_filter__function__get_expression() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> Q:
            return Q(created_at__lt=Now()) if value else Q(created_at__gte=Now())

    expr_1 = MyFilter.in_the_past.get_expression(value=True, info=mock_gql_info())
    assert expr_1 == Q(created_at__lt=Now())

    expr_2 = MyFilter.in_the_past.get_expression(value=False, info=mock_gql_info())
    assert expr_2 == Q(created_at__gte=Now())


def test_filter__function__get_field_type() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> Q: ...

    field_type = MyFilter.in_the_past.get_field_type()
    assert field_type == GraphQLBoolean


def test_filter__function__as_graphql_input_field() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        @Filter
        def in_the_past(self, *, value: bool) -> Q:
            """Filter tasks created in the past."""

    input_field = MyFilter.in_the_past.as_graphql_input_field()
    assert input_field.type == GraphQLBoolean
    assert input_field.description == "Filter tasks created in the past."
    assert input_field.deprecation_reason is None
    assert input_field.extensions == {"undine_filter": MyFilter.in_the_past}


def test_filter__function__with_args() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        @Filter(distinct=True)
        def in_the_past(self, *, value: bool) -> Q: ...

    assert MyFilter.in_the_past.distinct is True


def test_filter__lookup() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(lookup="in")

    assert MyFilter.name.lookup == "in"

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLList(GraphQLNonNull(GraphQLString))


def test_filter__many() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(many=True)

    assert MyFilter.name.many is True

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLList(GraphQLNonNull(GraphQLString))


def test_filter__match__all() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(match="all")

    assert MyFilter.name.match == ManyMatch.all
    assert MyFilter.name.match.operator == operator.and_


def test_filter__match__any() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(match="any")

    assert MyFilter.name.match == ManyMatch.any
    assert MyFilter.name.match.operator == operator.or_


def test_filter__match__one_of() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(match="one_of")

    assert MyFilter.name.match == ManyMatch.one_of
    assert MyFilter.name.match.operator == operator.xor


def test_filter__required() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(required=True)

    assert MyFilter.name.required is True

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLString)


def test_filter__many_and_required() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(many=True, required=True)

    assert MyFilter.name.many is True

    field_type = MyFilter.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


def test_filter__distinct() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(distinct=True)

    assert MyFilter.name.distinct is True


def test_filter__description() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(description="Description.")

    assert MyFilter.name.description == "Description."

    input_field = MyFilter.name.as_graphql_input_field()
    assert input_field.description == "Description."


def test_filter__description__variable() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter()
        """Description."""

    assert MyFilter.name.description == "Description."

    input_field = MyFilter.name.as_graphql_input_field()
    assert input_field.description == "Description."


def test_filter__deprecation_reason() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(deprecation_reason="Use something else.")

    assert MyFilter.name.deprecation_reason == "Use something else."

    input_field = MyFilter.name.as_graphql_input_field()
    assert input_field.deprecation_reason == "Use something else."


def test_filter__schema_name() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(schema_name="val")

    assert MyFilter.name.schema_name == "val"

    assert str(MyFilter.name) == "val: String"


def test_filter__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.INPUT_FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(directives=directives)

    assert MyFilter.name.directives == directives

    assert str(MyFilter.name) == 'name: String @value(value: "foo")'


def test_filter__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class MyFilter(FilterSet[Task], auto=False):
            name = Filter(directives=directives)

    # Model not cleaned up since error occurred in FilterSet class body.
    del FilterSetMeta.__model__


def test_filter__extensions() -> None:
    class MyFilter(FilterSet[Task], auto=False):
        name = Filter(extensions={"foo": "bar"})

    assert MyFilter.name.extensions == {"foo": "bar", "undine_filter": MyFilter.name}

    input_field = MyFilter.name.as_graphql_input_field()
    assert input_field.extensions == {"foo": "bar", "undine_filter": MyFilter.name}
