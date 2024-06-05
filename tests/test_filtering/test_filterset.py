import pytest
from django.db.models import Count, Q, Subquery
from graphql import GraphQLInputField

from example_project.app.models import Person, Task, TaskTypeChoices
from tests.helpers import MockGQLInfo
from undine.errors.exceptions import MissingModelError
from undine.filtering import Filter, FilterSet, get_filters_for_model

CREATED_AT_FIELDS = (
    "createdAtContains",
    "createdAtDay",
    "createdAtEndswith",
    "createdAtExact",
    "createdAtGt",
    "createdAtGte",
    "createdAtIcontains",
    "createdAtIendswith",
    "createdAtIexact",
    "createdAtIn",
    "createdAtIregex",
    "createdAtIsnull",
    "createdAtIsoWeekDay",
    "createdAtIsoYear",
    "createdAtIstartswith",
    "createdAtLt",
    "createdAtLte",
    "createdAtMonth",
    "createdAtQuarter",
    "createdAtRange",
    "createdAtRegex",
    "createdAtStartswith",
    "createdAtWeek",
    "createdAtWeekDay",
    "createdAtYear",
)

NAME_FIELDS = (
    "nameContains",
    "nameEndswith",
    "nameExact",
    "nameGt",
    "nameGte",
    "nameIcontains",
    "nameIendswith",
    "nameIexact",
    "nameIn",
    "nameIregex",
    "nameIsnull",
    "nameIstartswith",
    "nameLt",
    "nameLte",
    "nameRange",
    "nameRegex",
    "nameStartswith",
)

PK_FIELDS = (
    "pkContains",
    "pkEndswith",
    "pkExact",
    "pkGt",
    "pkGte",
    "pkIcontains",
    "pkIendswith",
    "pkIexact",
    "pkIn",
    "pkIregex",
    "pkIsnull",
    "pkIstartswith",
    "pkLt",
    "pkLte",
    "pkRange",
    "pkRegex",
    "pkStartswith",
)

TYPE_FIELDS = (
    "typeContains",
    "typeEndswith",
    "typeExact",
    "typeGt",
    "typeGte",
    "typeIcontains",
    "typeIendswith",
    "typeIexact",
    "typeIn",
    "typeIregex",
    "typeIsnull",
    "typeIstartswith",
    "typeLt",
    "typeLte",
    "typeRange",
    "typeRegex",
    "typeStartswith",
)


def test_filterset__attributes():
    class MyFilterSet(FilterSet, model=Task):
        """Decription."""

    assert MyFilterSet.__model__ == Task
    assert MyFilterSet.__typename__ == "MyFilterSet"
    assert MyFilterSet.__extensions__ == {"undine_filterset": MyFilterSet}


def test_filterset__input_type():
    class MyFilterSet(FilterSet, model=Task):
        """Decription."""

    input_type = MyFilterSet.__input_type__()

    assert input_type.name == "MyFilterSet"
    assert input_type.extensions == {"undine_filterset": MyFilterSet}
    assert input_type.description == "Decription."

    assert callable(input_type._fields)

    fields = input_type.fields
    filters = CREATED_AT_FIELDS + NAME_FIELDS + PK_FIELDS + TYPE_FIELDS

    assert all(field in fields for field in filters), set(filters) - set(fields)
    assert isinstance(fields["NOT"], GraphQLInputField)
    assert isinstance(fields["AND"], GraphQLInputField)
    assert isinstance(fields["OR"], GraphQLInputField)
    assert isinstance(fields["XOR"], GraphQLInputField)


def test_filterset__no_model():
    with pytest.raises(MissingModelError):

        class MyFilterSet(FilterSet): ...


def test_filterset__build__one_field():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "name_exact": "foo",
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo")]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__two_fields():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "name_exact": "foo",
        "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo"), Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__and_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "AND": {
            "name_exact": "foo",
            "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") & Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__or_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "name_exact": "foo",
            "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") | Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__xor_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "XOR": {
            "name_exact": "foo",
            "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") ^ Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__not_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "NOT": {
            "name_exact": "foo",
            "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [~Q(name__exact="foo"), ~Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__nested_blocks():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "NOT": {
                "name_exact": "foo",
                "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
            },
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [~Q(name__exact="foo") | ~Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__nested_blocks__complex():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "NOT": {
                "name_exact": "foo",
            },
            "AND": {
                "name_contains": "foo",
                "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
                "NOT": {
                    "type_exact": TaskTypeChoices.TASK.value,
                },
            },
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [
        ~Q(name__exact="foo")
        | (
            Q(name__contains="foo")
            & Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])
            & ~Q(type__exact=TaskTypeChoices.TASK)
        ),
    ]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__typename():
    class MyFilterSet(FilterSet, model=Task, typename="CustomName"): ...

    assert MyFilterSet.__typename__ == "CustomName"

    input_type = MyFilterSet.__input_type__()
    assert input_type.name == "CustomName"


def test_filterset__extensions():
    class MyFilterSet(FilterSet, model=Task, extensions={"foo": "bar"}): ...

    assert MyFilterSet.__extensions__ == {"foo": "bar", "undine_filterset": MyFilterSet}

    input_type = MyFilterSet.__input_type__()
    assert input_type.extensions == {"foo": "bar", "undine_filterset": MyFilterSet}


def test_filterset__no_auto():
    class MyFilterSet(FilterSet, model=Task, auto=False): ...

    assert MyFilterSet.__filter_map__ == {}


def test_filterset__exclude():
    class MyFilterSet(FilterSet, model=Task, exclude=["pk"]): ...

    fields = MyFilterSet.__input_type__().fields

    assert all(field in fields for field in CREATED_AT_FIELDS)
    assert all(field in fields for field in NAME_FIELDS)
    assert all(field not in fields for field in PK_FIELDS)
    assert all(field in fields for field in TYPE_FIELDS)


def test_filterset__exclude__multiple():
    class MyFilterSet(FilterSet, model=Task, exclude=["pk", "name"]): ...

    fields = MyFilterSet.__input_type__().fields

    assert all(field in fields for field in CREATED_AT_FIELDS)
    assert all(field not in fields for field in NAME_FIELDS)
    assert all(field not in fields for field in PK_FIELDS)
    assert all(field in fields for field in TYPE_FIELDS)


def test_filterset__expression():
    class MyFilterSet(FilterSet, model=Task, auto=False):
        assignee_count_lt = Filter(Count("assignees"), lookup="lt")

    data = {
        "assignee_count_lt": 1,
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(assignee_count_lt__lt=1)]
    assert results.distinct is False
    assert results.aliases == {"assignee_count_lt": Count("assignees")}


def test_filterset__subquery():
    sq = Subquery(Person.objects.values("name")[:1])

    class MyFilterSet(FilterSet, model=Task, auto=False):
        primary_assignee_name_in = Filter(sq, lookup="in")

    data = {
        "primary_assignee_name_in": ["foo", "bar"],
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(primary_assignee_name_in__in=["foo", "bar"])]
    assert results.distinct is False
    assert results.aliases == {"primary_assignee_name_in": sq}


def test_filterset__distinct():
    class MyFilterSet(FilterSet, model=Task, auto=False):
        assignee_name = Filter("assignees__name", distinct=True)

    data = {"assignee_name": "foo"}

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(assignees__name__exact="foo")]
    assert results.distinct is True
    assert results.aliases == {}


def test_filterset__many__any():
    class MyFilterSet(FilterSet, model=Task, auto=False):
        name = Filter(many=True)

    data = {"name": ["foo", "bar"]}

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") | Q(name__exact="bar")]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__many__all():
    class MyFilterSet(FilterSet, model=Task, auto=False):
        name = Filter(many=True, match="all")

    data = {"name": ["foo", "bar"]}

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") & Q(name__exact="bar")]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__required_aliases():
    class MyFilterSet(FilterSet, model=Task, auto=False):
        name = Filter(required_aliases={"foo": Count("*")})

    data = {"name": "foo"}

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo")]
    assert results.distinct is False
    assert results.aliases == {"foo": Count("*")}


def test_filterset__get_filters_for_model():
    filters = get_filters_for_model(Task, exclude=[])

    # TODO: Go through all filters and check if they make sense.
    assert sorted(filters) == [
        "attachment_contains",
        "attachment_endswith",
        "attachment_exact",
        "attachment_gt",
        "attachment_gte",
        "attachment_icontains",
        "attachment_iendswith",
        "attachment_iexact",
        "attachment_in",
        "attachment_iregex",
        "attachment_isnull",
        "attachment_istartswith",
        "attachment_lt",
        "attachment_lte",
        "attachment_range",
        "attachment_regex",
        "attachment_startswith",
        "check_time_contains",
        "check_time_endswith",
        "check_time_exact",
        "check_time_gt",
        "check_time_gte",
        "check_time_hour",
        "check_time_icontains",
        "check_time_iendswith",
        "check_time_iexact",
        "check_time_in",
        "check_time_iregex",
        "check_time_isnull",
        "check_time_istartswith",
        "check_time_lt",
        "check_time_lte",
        "check_time_minute",
        "check_time_range",
        "check_time_regex",
        "check_time_second",
        "check_time_startswith",
        "contact_email_contains",
        "contact_email_endswith",
        "contact_email_exact",
        "contact_email_gt",
        "contact_email_gte",
        "contact_email_icontains",
        "contact_email_iendswith",
        "contact_email_iexact",
        "contact_email_in",
        "contact_email_iregex",
        "contact_email_isnull",
        "contact_email_istartswith",
        "contact_email_lt",
        "contact_email_lte",
        "contact_email_range",
        "contact_email_regex",
        "contact_email_startswith",
        "created_at_contained_by",
        "created_at_contains",
        "created_at_date",
        "created_at_day",
        "created_at_endswith",
        "created_at_exact",
        "created_at_gt",
        "created_at_gte",
        "created_at_hour",
        "created_at_icontains",
        "created_at_iendswith",
        "created_at_iexact",
        "created_at_in",
        "created_at_iregex",
        "created_at_isnull",
        "created_at_iso_week_day",
        "created_at_iso_year",
        "created_at_istartswith",
        "created_at_lt",
        "created_at_lte",
        "created_at_minute",
        "created_at_month",
        "created_at_quarter",
        "created_at_range",
        "created_at_regex",
        "created_at_second",
        "created_at_startswith",
        "created_at_time",
        "created_at_week",
        "created_at_week_day",
        "created_at_year",
        "demo_url_contains",
        "demo_url_endswith",
        "demo_url_exact",
        "demo_url_gt",
        "demo_url_gte",
        "demo_url_icontains",
        "demo_url_iendswith",
        "demo_url_iexact",
        "demo_url_in",
        "demo_url_iregex",
        "demo_url_isnull",
        "demo_url_istartswith",
        "demo_url_lt",
        "demo_url_lte",
        "demo_url_range",
        "demo_url_regex",
        "demo_url_startswith",
        "done_contains",
        "done_endswith",
        "done_exact",
        "done_gt",
        "done_gte",
        "done_icontains",
        "done_iendswith",
        "done_iexact",
        "done_in",
        "done_iregex",
        "done_isnull",
        "done_istartswith",
        "done_lt",
        "done_lte",
        "done_range",
        "done_regex",
        "done_startswith",
        "due_by_contained_by",
        "due_by_contains",
        "due_by_day",
        "due_by_endswith",
        "due_by_exact",
        "due_by_gt",
        "due_by_gte",
        "due_by_icontains",
        "due_by_iendswith",
        "due_by_iexact",
        "due_by_in",
        "due_by_iregex",
        "due_by_isnull",
        "due_by_iso_week_day",
        "due_by_iso_year",
        "due_by_istartswith",
        "due_by_lt",
        "due_by_lte",
        "due_by_month",
        "due_by_quarter",
        "due_by_range",
        "due_by_regex",
        "due_by_startswith",
        "due_by_week",
        "due_by_week_day",
        "due_by_year",
        "external_uuid_contains",
        "external_uuid_endswith",
        "external_uuid_exact",
        "external_uuid_gt",
        "external_uuid_gte",
        "external_uuid_icontains",
        "external_uuid_iendswith",
        "external_uuid_iexact",
        "external_uuid_in",
        "external_uuid_iregex",
        "external_uuid_isnull",
        "external_uuid_istartswith",
        "external_uuid_lt",
        "external_uuid_lte",
        "external_uuid_range",
        "external_uuid_regex",
        "external_uuid_startswith",
        "extra_data_contained_by",
        "extra_data_contains",
        "extra_data_endswith",
        "extra_data_exact",
        "extra_data_gt",
        "extra_data_gte",
        "extra_data_has_any_keys",
        "extra_data_has_key",
        "extra_data_has_keys",
        "extra_data_icontains",
        "extra_data_iendswith",
        "extra_data_iexact",
        "extra_data_in",
        "extra_data_iregex",
        "extra_data_isnull",
        "extra_data_istartswith",
        "extra_data_lt",
        "extra_data_lte",
        "extra_data_range",
        "extra_data_regex",
        "extra_data_startswith",
        "image_contains",
        "image_endswith",
        "image_exact",
        "image_gt",
        "image_gte",
        "image_icontains",
        "image_iendswith",
        "image_iexact",
        "image_in",
        "image_iregex",
        "image_isnull",
        "image_istartswith",
        "image_lt",
        "image_lte",
        "image_range",
        "image_regex",
        "image_startswith",
        "name_contains",
        "name_endswith",
        "name_exact",
        "name_gt",
        "name_gte",
        "name_icontains",
        "name_iendswith",
        "name_iexact",
        "name_in",
        "name_iregex",
        "name_isnull",
        "name_istartswith",
        "name_lt",
        "name_lte",
        "name_range",
        "name_regex",
        "name_startswith",
        "pk_contained_by",
        "pk_contains",
        "pk_endswith",
        "pk_exact",
        "pk_gt",
        "pk_gte",
        "pk_icontains",
        "pk_iendswith",
        "pk_iexact",
        "pk_in",
        "pk_iregex",
        "pk_isnull",
        "pk_istartswith",
        "pk_lt",
        "pk_lte",
        "pk_range",
        "pk_regex",
        "pk_startswith",
        "points_contained_by",
        "points_contains",
        "points_endswith",
        "points_exact",
        "points_gt",
        "points_gte",
        "points_icontains",
        "points_iendswith",
        "points_iexact",
        "points_in",
        "points_iregex",
        "points_isnull",
        "points_istartswith",
        "points_lt",
        "points_lte",
        "points_range",
        "points_regex",
        "points_startswith",
        "progress_contained_by",
        "progress_contains",
        "progress_endswith",
        "progress_exact",
        "progress_gt",
        "progress_gte",
        "progress_icontains",
        "progress_iendswith",
        "progress_iexact",
        "progress_in",
        "progress_iregex",
        "progress_isnull",
        "progress_istartswith",
        "progress_lt",
        "progress_lte",
        "progress_range",
        "progress_regex",
        "progress_startswith",
        "type_contains",
        "type_endswith",
        "type_exact",
        "type_gt",
        "type_gte",
        "type_icontains",
        "type_iendswith",
        "type_iexact",
        "type_in",
        "type_iregex",
        "type_isnull",
        "type_istartswith",
        "type_lt",
        "type_lte",
        "type_range",
        "type_regex",
        "type_startswith",
        "worked_hours_contains",
        "worked_hours_endswith",
        "worked_hours_exact",
        "worked_hours_gt",
        "worked_hours_gte",
        "worked_hours_icontains",
        "worked_hours_iendswith",
        "worked_hours_iexact",
        "worked_hours_in",
        "worked_hours_iregex",
        "worked_hours_isnull",
        "worked_hours_istartswith",
        "worked_hours_lt",
        "worked_hours_lte",
        "worked_hours_range",
        "worked_hours_regex",
        "worked_hours_startswith",
    ]
