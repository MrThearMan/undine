from django.db.models import Q

from example_project.app.models import Task, TaskType
from tests.helpers import MockGQLInfo
from undine.filtering import FilterSet


def test_filterset__default():
    class MyFilterSet(FilterSet, model=Task): ...

    assert MyFilterSet.__model__ == Task
    assert MyFilterSet.__typename__ == "MyFilterSet"
    assert MyFilterSet.__extensions__ == {"undine_filter_input": MyFilterSet}

    filter_map = MyFilterSet.__filter_map__

    assert sorted(filter_map) == [
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
    ]

    input_type = MyFilterSet.__input_type__()

    assert input_type.name == "MyFilterSet"


def test_filterset__one_field():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "nameExact": "foo",
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo")]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__two_fields():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "nameExact": "foo",
        "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo"), Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__and_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "AND": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") & Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__or_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") | Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__xor_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "XOR": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") ^ Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__not_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "NOT": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [~Q(name__exact="foo"), ~Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__nested_blocks():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "NOT": {
                "nameExact": "foo",
                "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
            },
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [~Q(name__exact="foo") | ~Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__nested_blocks__complex():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "NOT": {
                "nameExact": "foo",
            },
            "AND": {
                "nameContains": "foo",
                "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
                "NOT": {
                    "typeExact": TaskType.TASK.value,
                },
            },
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [
        ~Q(name__exact="foo")
        | (Q(name__contains="foo") & Q(type__in=[TaskType.BUG_FIX, TaskType.STORY]) & ~Q(type__exact=TaskType.TASK)),
    ]
    assert results.distinct is False
    assert results.aliases == {}
