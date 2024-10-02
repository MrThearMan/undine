from django.db.models import Q

from example_project.app.models import Task, TaskType
from tests.helpers import MockGQLInfo
from undine import ModelGQLFilter


def test_model_filter__default():
    class MyFilter(ModelGQLFilter, model=Task): ...

    assert MyFilter.__model__ == Task
    assert MyFilter.__typename__ == "MyFilter"
    assert MyFilter.__extensions__ == {"undine_filter_input": MyFilter}

    filter_map = MyFilter.__filter_map__

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

    input_type = MyFilter.__input_type__()

    assert input_type.name == "MyFilter"


def test_model_filter__one_field():
    class MyFilter(ModelGQLFilter, model=Task): ...

    data = {
        "nameExact": "foo",
    }

    results = MyFilter.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo")]
    assert results.distinct is False
    assert results.aliases == {}


def test_model_filter__two_fields():
    class MyFilter(ModelGQLFilter, model=Task): ...

    data = {
        "nameExact": "foo",
        "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
    }

    results = MyFilter.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo"), Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_model_filter__and_block():
    class MyFilter(ModelGQLFilter, model=Task): ...

    data = {
        "AND": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilter.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") & Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_model_filter__or_block():
    class MyFilter(ModelGQLFilter, model=Task): ...

    data = {
        "OR": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilter.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") | Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_model_filter__xor_block():
    class MyFilter(ModelGQLFilter, model=Task): ...

    data = {
        "XOR": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilter.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") ^ Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_model_filter__not_block():
    class MyFilter(ModelGQLFilter, model=Task): ...

    data = {
        "NOT": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilter.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [~Q(name__exact="foo"), ~Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_model_filter__nested_blocks():
    class MyFilter(ModelGQLFilter, model=Task): ...

    data = {
        "OR": {
            "NOT": {
                "nameExact": "foo",
                "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
            },
        },
    }

    results = MyFilter.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [~Q(name__exact="foo") | ~Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_model_filter__nested_blocks__complex():
    class MyFilter(ModelGQLFilter, model=Task): ...

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

    results = MyFilter.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [
        ~Q(name__exact="foo")
        | (Q(name__contains="foo") & Q(type__in=[TaskType.BUG_FIX, TaskType.STORY]) & ~Q(type__exact=TaskType.TASK)),
    ]
    assert results.distinct is False
    assert results.aliases == {}
