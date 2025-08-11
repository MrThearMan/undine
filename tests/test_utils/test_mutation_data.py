from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model

from example_project.example.models import (
    Example,
    ExampleFFK,
    ExampleFMTM,
    ExampleFOTO,
    ExampleGeneric,
    ExampleRFK,
    ExampleRMTM,
    ExampleROTO,
    NestedExampleFFK,
    NestedExampleFMTM,
    NestedExampleFOTO,
    NestedExampleRFK,
    NestedExampleRMTM,
    NestedExampleROTO,
)
from pytest_undine.query_logging import capture_database_queries
from tests.factories.example import (
    ExampleFactory,
    ExampleFFKFactory,
    ExampleFMTMFactory,
    ExampleFOTOFactory,
    ExampleRFKFactory,
    ExampleRMTMFactory,
    ExampleROTOFactory,
)
from undine.utils.mutation_data import MutationData, MutationManyData, get_mutation_data


@pytest.mark.django_db
def test_mutation_data(undine_settings):
    undine_settings.MUTATION_INSTANCE_LIMIT = 200

    example = ExampleFactory.create(name="bar")

    count = 3

    nested = {
        "name": "foo",
        "example_foto": {"name": "foo"},
        "example_ffk": {"name": "foo"},
        "example_fmtm_set": [{"name": "foo"} for _ in range(count)],
        "example_roto": {"name": "foo"},
        "example_rfk_set": [{"name": "foo"} for _ in range(count)],
        "example_rmtm_set": [{"name": "foo"} for _ in range(count)],
    }
    data = {
        "pk": example.pk,
        "name": "foo",
        "example_foto": nested,
        "example_ffk": nested,
        "example_fmtm_set": [nested for _ in range(count)],
        "example_roto": nested,
        "example_rfk_set": [nested for _ in range(count)],
        "example_rmtm_set": [nested for _ in range(count)],
    }

    with capture_database_queries() as queries:
        mutation_data = get_mutation_data(model=Example, data=data)

    assert queries.count == 1, queries.log

    assert isinstance(mutation_data, MutationData)
    assert mutation_data.instance == example

    assert list(mutation_data.data) == [
        "pk",
        "name",
        "example_foto",
        "example_ffk",
        "example_roto",
        "example_fmtm_set",
        "example_rfk_set",
        "example_rmtm_set",
    ]

    assert mutation_data.data["pk"] == example.pk
    assert mutation_data.data["name"] == "foo"

    _check_single(mutation_data.data["example_foto"], ExampleFOTO, count=count)
    _check_single(mutation_data.data["example_ffk"], ExampleFFK, count=count)
    _check_single(mutation_data.data["example_roto"], ExampleROTO, count=count)

    _check_many(mutation_data.data["example_fmtm_set"], ExampleFMTM, count=count)
    _check_many(mutation_data.data["example_rfk_set"], ExampleRFK, count=count)
    _check_many(mutation_data.data["example_rmtm_set"], ExampleRMTM, count=count)


@pytest.mark.django_db
def test_mutation_data__ids():
    example_foto = ExampleFOTOFactory.create()
    example_ffk = ExampleFFKFactory.create()
    example_fmtm = ExampleFMTMFactory.create()
    example_roto = ExampleROTOFactory.create()
    example_rfk = ExampleRFKFactory.create()
    example_rmtm = ExampleRMTMFactory.create()

    data = {
        "name": "foo",
        "example_foto": example_foto.pk,
        "example_ffk": example_ffk.pk,
        "example_fmtm_set": [example_fmtm.pk],
        "example_roto": example_roto.pk,
        "example_rfk_set": [example_rfk.pk],
        "example_rmtm_set": [example_rmtm.pk],
    }

    with capture_database_queries() as queries:
        mutation_data = get_mutation_data(model=Example, data=data)

    assert queries.count == 6, queries.log

    assert isinstance(mutation_data, MutationData)
    assert isinstance(mutation_data.instance, Example)
    assert mutation_data.instance.pk is None
    assert list(mutation_data.data) == [
        "name",
        "example_foto",
        "example_ffk",
        "example_roto",
        "example_fmtm_set",
        "example_rfk_set",
        "example_rmtm_set",
    ]

    _check_single_id(mutation_data.data["example_foto"], ExampleFOTO, pk=example_foto.pk)
    _check_single_id(mutation_data.data["example_ffk"], ExampleFFK, pk=example_ffk.pk)
    _check_single_id(mutation_data.data["example_roto"], ExampleROTO, pk=example_roto.pk)

    _check_many_id(mutation_data.data["example_fmtm_set"], ExampleFMTM, pk=example_fmtm.pk)
    _check_many_id(mutation_data.data["example_rfk_set"], ExampleRFK, pk=example_rfk.pk)
    _check_many_id(mutation_data.data["example_rmtm_set"], ExampleRMTM, pk=example_rmtm.pk)


@pytest.mark.django_db
def test_mutation_data__null():
    data = {
        "name": "foo",
        "example_foto": None,
        "example_ffk": None,
        "example_fmtm_set": None,
        "example_roto": None,
        "example_rfk_set": None,
        "example_rmtm_set": None,
    }

    with capture_database_queries() as queries:
        mutation_data = get_mutation_data(model=Example, data=data)

    assert queries.count == 0, queries.log

    assert isinstance(mutation_data, MutationData)
    assert isinstance(mutation_data.instance, Example)
    assert mutation_data.instance.pk is None
    assert list(mutation_data.data) == [
        "name",
        "example_foto",
        "example_ffk",
        "example_roto",
        "example_fmtm_set",
        "example_rfk_set",
        "example_rmtm_set",
    ]

    _check_single_null(mutation_data.data["example_foto"])
    _check_single_null(mutation_data.data["example_ffk"])
    _check_single_null(mutation_data.data["example_roto"])

    _check_many_null(mutation_data.data["example_fmtm_set"])
    _check_many_null(mutation_data.data["example_rfk_set"])
    _check_many_null(mutation_data.data["example_rmtm_set"])


@pytest.mark.django_db
def test_mutation_data__generic_relation():
    data = {
        "name": "foo",
        "generic": [
            {
                "name": "bar",
            },
            {
                "name": "baz",
            },
        ],
    }

    with capture_database_queries() as queries:
        mutation_data = get_mutation_data(model=Example, data=data)

    assert queries.count == 0, queries.log

    assert isinstance(mutation_data, MutationData)
    assert isinstance(mutation_data.instance, Example)
    assert mutation_data.instance.pk is None
    assert list(mutation_data.data) == ["name", "generic"]

    generic_data = mutation_data.data["generic"]
    assert isinstance(generic_data, MutationManyData)
    assert len(generic_data) == 2

    generic_data_1 = generic_data[0]
    generic_data_2 = generic_data[1]

    assert isinstance(generic_data_1, MutationData)
    assert isinstance(generic_data_1.instance, ExampleGeneric)
    assert generic_data_1.instance.pk is None
    assert list(generic_data_1.data) == ["name"]
    assert generic_data_1.data["name"] == "bar"

    assert isinstance(generic_data_2, MutationData)
    assert isinstance(generic_data_2.instance, ExampleGeneric)
    assert generic_data_2.instance.pk is None
    assert list(generic_data_2.data) == ["name"]
    assert generic_data_2.data["name"] == "baz"


@pytest.mark.django_db
def test_mutation_data__generic_foreign_key():
    # Cache the content type
    ContentType.objects.get_for_model(Example)

    data = {
        "name": "bar",
        "content_object": {
            "example": {
                "name": "foo",
            },
        },
    }

    with capture_database_queries() as queries:
        mutation_data = get_mutation_data(model=ExampleGeneric, data=data)

    assert queries.count == 0, queries.log

    assert isinstance(mutation_data, MutationData)
    assert isinstance(mutation_data.instance, ExampleGeneric)
    assert mutation_data.instance.pk is None
    assert list(mutation_data.data) == ["name", "content_object"]

    generic_data = mutation_data.data["content_object"]
    assert isinstance(generic_data, MutationData)
    assert isinstance(generic_data.instance, Example)
    assert generic_data.instance.pk is None
    assert list(generic_data.data) == ["name"]
    assert generic_data.data["name"] == "foo"


@pytest.mark.django_db
def test_mutation_data__generic_foreign_key__ids():
    # Cache the content type
    ContentType.objects.get_for_model(Example)

    example = ExampleFactory.create(name="foo")

    data = {
        "name": "bar",
        "content_object": {
            "example": {
                "pk": example.pk,
            },
        },
    }

    with capture_database_queries() as queries:
        mutation_data = get_mutation_data(model=ExampleGeneric, data=data)

    assert queries.count == 1, queries.log

    assert isinstance(mutation_data, MutationData)
    assert isinstance(mutation_data.instance, ExampleGeneric)
    assert mutation_data.instance.pk is None
    assert list(mutation_data.data) == ["name", "content_object"]

    generic_data = mutation_data.data["content_object"]
    assert isinstance(generic_data, MutationData)
    assert generic_data.instance == example
    assert list(generic_data.data) == ["pk"]
    assert generic_data.data["pk"] == example.pk


# ---------------------------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------------------------


def _check_single(mutation_data: Any, model: type[Model], *, count: int) -> None:
    assert isinstance(mutation_data, MutationData)
    assert isinstance(mutation_data.instance, model)
    assert mutation_data.instance.pk is None

    assert list(mutation_data.data) == [
        "name",
        "example_foto",
        "example_ffk",
        "example_roto",
        "example_fmtm_set",
        "example_rfk_set",
        "example_rmtm_set",
    ]

    assert mutation_data.data["name"] == "foo"

    _check_nested(mutation_data, count=count)


def _check_many(mutation_data: Any, model: type[Model], *, count: int) -> None:
    assert isinstance(mutation_data, MutationManyData)
    assert len(mutation_data) == count

    for mutation_data_item in mutation_data:
        assert isinstance(mutation_data_item, MutationData)
        assert isinstance(mutation_data_item.instance, model)
        assert mutation_data_item.instance.pk is None
        assert list(mutation_data_item.data) == [
            "name",
            "example_foto",
            "example_ffk",
            "example_roto",
            "example_fmtm_set",
            "example_rfk_set",
            "example_rmtm_set",
        ]

        assert mutation_data_item.data["name"] == "foo"

        _check_nested(mutation_data_item, count=count)


def _check_nested(mutation_data: MutationData, *, count: int) -> None:
    _check_nested_single(mutation_data.data["example_foto"], NestedExampleFOTO)
    _check_nested_single(mutation_data.data["example_ffk"], NestedExampleFFK)
    _check_nested_single(mutation_data.data["example_roto"], NestedExampleROTO)

    _check_nested_many(mutation_data.data["example_fmtm_set"], NestedExampleFMTM, count=count)
    _check_nested_many(mutation_data.data["example_rfk_set"], NestedExampleRFK, count=count)
    _check_nested_many(mutation_data.data["example_rmtm_set"], NestedExampleRMTM, count=count)


def _check_nested_single(mutation_type: Any, model: type[Model]) -> None:
    assert isinstance(mutation_type, MutationData)
    assert isinstance(mutation_type.instance, model)
    assert mutation_type.instance.pk is None
    assert list(mutation_type.data) == ["name"]


def _check_nested_many(mutation_type: Any, model: type[Model], *, count: int) -> None:
    assert isinstance(mutation_type, MutationManyData)
    assert len(mutation_type) == count
    for mutation_type_item in mutation_type:
        assert isinstance(mutation_type_item, MutationData)
        assert isinstance(mutation_type_item.instance, model)
        assert mutation_type_item.instance.pk is None
        assert list(mutation_type_item.data) == ["name"]


def _check_single_id(mutation_data: Any, model: type[Model], *, pk: int) -> None:
    assert isinstance(mutation_data, MutationData)
    assert isinstance(mutation_data.instance, model)
    assert mutation_data.instance.pk == pk
    assert list(mutation_data.data) == ["pk"]
    assert mutation_data.data["pk"] == pk


def _check_many_id(mutation_data: Any, model: type[Model], *, pk: int) -> None:
    assert isinstance(mutation_data, MutationManyData)
    assert len(mutation_data) == 1

    for mutation_data_item in mutation_data:
        assert isinstance(mutation_data_item, MutationData)
        assert isinstance(mutation_data_item.instance, model)
        assert mutation_data_item.instance.pk == pk
        assert list(mutation_data_item.data) == ["pk"]
        assert mutation_data_item.data["pk"] == pk


def _check_single_null(mutation_data: Any) -> None:
    assert mutation_data is None


def _check_many_null(mutation_data: Any) -> None:
    assert isinstance(mutation_data, MutationManyData)
    assert len(mutation_data) == 0
