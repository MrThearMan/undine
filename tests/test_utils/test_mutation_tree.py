from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType

from example_project.example.models import Example, ExampleGeneric
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
from undine.utils.mutation_tree import mutate


@pytest.mark.django_db
def test_mutation_optimization(undine_settings) -> None:  # noqa: C901, PLR0912
    undine_settings.MUTATION_FULL_CLEAN = False

    ex = ExampleFactory.create(name="bar")

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
        "pk": ex.pk,
        "name": "foo",
        "example_foto": nested,
        "example_ffk": nested,
        "example_fmtm_set": [nested for _ in range(count)],
        "example_roto": nested,
        "example_rfk_set": [nested for _ in range(count)],
        "example_rmtm_set": [nested for _ in range(count)],
    }

    with capture_database_queries() as queries:
        example = mutate(data, model=Example)

    assert queries.count == 88, queries.log

    example.refresh_from_db()

    assert example.pk == ex.pk
    assert example.name == "foo"

    # example_foto
    assert example.example_foto.name == "foo"
    assert example.example_foto.example_foto.name == "foo"
    assert example.example_foto.example_ffk.name == "foo"
    assert example.example_foto.example_roto.name == "foo"

    assert example.example_foto.example_fmtm_set.count() == count
    for example_fmtm in example.example_foto.example_fmtm_set.all():
        assert example_fmtm.name == "foo"

    assert example.example_foto.example_rfk_set.count() == count
    for example_rfk in example.example_foto.example_rfk_set.all():
        assert example_rfk.name == "foo"

    assert example.example_foto.example_rmtm_set.count() == count
    for example_rmtm in example.example_foto.example_rmtm_set.all():
        assert example_rmtm.name == "foo"

    # example_ffk
    assert example.example_ffk.name == "foo"
    assert example.example_ffk.example_foto.name == "foo"
    assert example.example_ffk.example_ffk.name == "foo"
    assert example.example_ffk.example_roto.name == "foo"

    assert example.example_ffk.example_fmtm_set.count() == count
    for example_fmtm in example.example_ffk.example_fmtm_set.all():
        assert example_fmtm.name == "foo"

    assert example.example_ffk.example_rfk_set.count() == count
    for example_rfk in example.example_ffk.example_rfk_set.all():
        assert example_rfk.name == "foo"

    assert example.example_ffk.example_rmtm_set.count() == count
    for example_rmtm in example.example_ffk.example_rmtm_set.all():
        assert example_rmtm.name == "foo"

    # example_roto
    assert example.example_roto.name == "foo"
    assert example.example_roto.example_foto.name == "foo"
    assert example.example_roto.example_ffk.name == "foo"
    assert example.example_roto.example_roto.name == "foo"

    assert example.example_roto.example_fmtm_set.count() == count
    for example_fmtm in example.example_roto.example_fmtm_set.all():
        assert example_fmtm.name == "foo"

    assert example.example_roto.example_rfk_set.count() == count
    for example_rfk in example.example_roto.example_rfk_set.all():
        assert example_rfk.name == "foo"

    assert example.example_roto.example_rmtm_set.count() == count
    for example_rmtm in example.example_roto.example_rmtm_set.all():
        assert example_rmtm.name == "foo"

    # example_fmtm_set
    assert example.example_fmtm_set.count() == count
    for example_fmtm in example.example_fmtm_set.all():
        assert example_fmtm.name == "foo"
        assert example_fmtm.example_foto.name == "foo"
        assert example_fmtm.example_ffk.name == "foo"
        assert example_fmtm.example_roto.name == "foo"

        assert example_fmtm.example_fmtm_set.count() == count
        for nested_example_fmtm in example_fmtm.example_fmtm_set.all():
            assert nested_example_fmtm.name == "foo"

        assert example_fmtm.example_rfk_set.count() == count
        for nested_example_rfk in example_fmtm.example_rfk_set.all():
            assert nested_example_rfk.name == "foo"

        assert example_fmtm.example_rmtm_set.count() == count
        for nested_example_rmtm in example_fmtm.example_rmtm_set.all():
            assert nested_example_rmtm.name == "foo"

    # example_rfk_set
    assert example.example_rfk_set.count() == count
    for example_rfk in example.example_rfk_set.all():
        assert example_rfk.name == "foo"
        assert example_rfk.example_foto.name == "foo"
        assert example_rfk.example_ffk.name == "foo"
        assert example_rfk.example_roto.name == "foo"

        assert example_rfk.example_fmtm_set.count() == count
        for nested_example_fmtm in example_rfk.example_fmtm_set.all():
            assert nested_example_fmtm.name == "foo"

        assert example_rfk.example_rfk_set.count() == count
        for nested_example_rfk in example_rfk.example_rfk_set.all():
            assert nested_example_rfk.name == "foo"

        assert example_rfk.example_rmtm_set.count() == count
        for nested_example_rmtm in example_rfk.example_rmtm_set.all():
            assert nested_example_rmtm.name == "foo"

    # example_rmtm_set
    assert example.example_rmtm_set.count() == count
    for example_rmtm in example.example_rmtm_set.all():
        assert example_rmtm.name == "foo"
        assert example_rmtm.example_foto.name == "foo"
        assert example_rmtm.example_ffk.name == "foo"
        assert example_rmtm.example_roto.name == "foo"

        assert example_rmtm.example_fmtm_set.count() == count
        for nested_example_fmtm in example_rmtm.example_fmtm_set.all():
            assert nested_example_fmtm.name == "foo"

        assert example_rmtm.example_rfk_set.count() == count
        for nested_example_rfk in example_rmtm.example_rfk_set.all():
            assert nested_example_rfk.name == "foo"

        assert example_rmtm.example_rmtm_set.count() == count
        for nested_example_rmtm in example_rmtm.example_rmtm_set.all():
            assert nested_example_rmtm.name == "foo"


@pytest.mark.django_db
def test_mutation_optimization__ids(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

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
        example = mutate(data, model=Example)

    assert queries.count == 15, queries.log

    example.refresh_from_db()

    assert example.name == "foo"

    assert example.example_foto.pk == example_foto.pk
    assert example.example_ffk.pk == example_ffk.pk
    assert example.example_roto.pk == example_roto.pk

    assert example.example_fmtm_set.count() == 1
    assert example.example_fmtm_set.first().pk == example_fmtm.pk

    assert example.example_rfk_set.count() == 1
    assert example.example_rfk_set.first().pk == example_rfk.pk

    assert example.example_rmtm_set.count() == 1
    assert example.example_rmtm_set.first().pk == example_rmtm.pk


@pytest.mark.django_db
def test_mutation_optimization__null(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

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
        example = mutate(data, model=Example)

    assert queries.count == 3, queries.log

    example.refresh_from_db()

    assert example.name == "foo"

    assert example.example_foto is None
    assert example.example_ffk is None
    assert getattr(example, "example_roto", None) is None
    assert list(example.example_fmtm_set.all()) == []
    assert list(example.example_rfk_set.all()) == []
    assert list(example.example_rmtm_set.all()) == []


@pytest.mark.django_db
def test_mutation_optimization__set_null(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    example = ExampleFactory.create(
        name="foo",
        example_foto__name="foo",
        example_ffk__name="foo",
        example_fmtm_set__name="foo",
        example_roto__name="foo",
        example_rfk_set__name="foo",
        example_rmtm_set__name="foo",
    )

    data = {
        "pk": example.pk,
        "example_foto": None,
        "example_ffk": None,
        "example_fmtm_set": None,
        "example_roto": None,
        "example_rfk_set": None,
        "example_rmtm_set": None,
    }

    with capture_database_queries() as queries:
        example = mutate(data, model=Example)

    assert queries.count == 10, queries.log

    example.refresh_from_db()

    assert example.name == "foo"

    assert example.example_foto is None
    assert example.example_ffk is None
    assert getattr(example, "example_roto", None) is None
    assert list(example.example_fmtm_set.all()) == []
    assert list(example.example_rfk_set.all()) == []
    assert list(example.example_rmtm_set.all()) == []


@pytest.mark.django_db
def test_mutation_optimization__replace(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    example = ExampleFactory.create(
        name="foo",
        example_foto__name="foo",
        example_ffk__name="foo",
        example_fmtm_set__name="foo",
        example_roto__name="foo",
        example_rfk_set__name="foo",
        example_rmtm_set__name="foo",
    )

    data = {
        "pk": example.pk,
        "name": "bar",
        "example_foto": {"name": "bar"},
        "example_ffk": {"name": "bar"},
        "example_fmtm_set": [{"name": "bar"}],
        "example_roto": {"name": "bar"},
        "example_rfk_set": [{"name": "bar"}],
        "example_rmtm_set": [{"name": "bar"}],
    }

    with capture_database_queries() as queries:
        example = mutate(data, model=Example)

    assert queries.count == 20, queries.log

    example.refresh_from_db()

    assert example.name == "bar"

    assert example.example_foto.name == "bar"
    assert example.example_ffk.name == "bar"
    assert example.example_roto.name == "bar"

    assert example.example_fmtm_set.count() == 1
    assert example.example_fmtm_set.first().name == "bar"

    assert example.example_rfk_set.count() == 1
    assert example.example_rfk_set.first().name == "bar"

    assert example.example_rmtm_set.count() == 1
    assert example.example_rmtm_set.first().name == "bar"


@pytest.mark.django_db
def test_mutation_optimization__create_symmetrical(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    existing_example = ExampleFactory.create(name="foo")

    data = {
        "name": "bar",
        "symmetrical_field": [existing_example.pk],
    }

    with capture_database_queries() as queries:
        new_example = mutate(data, model=Example)

    assert queries.count == 5, queries.log

    assert new_example.name == "bar"
    assert new_example.symmetrical_field.count() == 1
    assert new_example.symmetrical_field.first().name == "foo"

    existing_example.refresh_from_db()
    assert existing_example.name == "foo"
    assert existing_example.symmetrical_field.count() == 1
    assert existing_example.symmetrical_field.first().name == "bar"


@pytest.mark.django_db
def test_mutation_optimization__add_symmetrical(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    example_1 = ExampleFactory.create(name="foo")
    example_2 = ExampleFactory.create(name="bar")
    example_1.symmetrical_field.add(example_2)

    data = {
        "name": "baz",
        "symmetrical_field": [example_1.pk],
    }

    with capture_database_queries() as queries:
        new_example = mutate(data, model=Example)

    assert queries.count == 5, queries.log

    assert new_example.name == "baz"
    assert new_example.symmetrical_field.count() == 1
    assert new_example.symmetrical_field.first().name == "foo"

    example_1.refresh_from_db()
    assert example_1.name == "foo"
    assert example_1.symmetrical_field.count() == 2
    assert example_1.symmetrical_field.all()[0].name == "bar"
    assert example_1.symmetrical_field.all()[1].name == "baz"

    example_2.refresh_from_db()
    assert example_2.name == "bar"
    assert example_2.symmetrical_field.count() == 1
    assert example_2.symmetrical_field.first().name == "foo"


@pytest.mark.django_db
def test_mutation_optimization__remove_symmetrical(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    example_1 = ExampleFactory.create(name="foo")
    example_2 = ExampleFactory.create(name="bar")
    example_1.symmetrical_field.add(example_2)

    data = {
        "pk": example_1.pk,
        "symmetrical_field": [],
    }

    with capture_database_queries() as queries:
        mutate(data, model=Example)

    assert queries.count == 3, queries.log

    example_1.refresh_from_db()
    assert example_1.symmetrical_field.count() == 0

    example_2.refresh_from_db()
    assert example_2.symmetrical_field.count() == 0


@pytest.mark.django_db
def test_mutation_optimization__generic_relation(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

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
        example = mutate(data, model=Example)

    assert queries.count == 3, queries.log

    assert example.name == "foo"

    generics = list(example.generic.all())
    assert len(generics) == 2
    assert generics[0].name == "bar"
    assert generics[1].name == "baz"


@pytest.mark.django_db
def test_mutation_optimization__generic_foreign_key(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

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
        example_generic = mutate(data, model=ExampleGeneric)

    assert queries.count == 2, queries.log

    assert example_generic.name == "bar"
    assert example_generic.content_object.name == "foo"


@pytest.mark.django_db
def test_mutation_optimization__generic_foreign_key__pk(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

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
        example_generic = mutate(data, model=ExampleGeneric)

    assert queries.count == 2, queries.log

    assert example_generic.name == "bar"
    assert example_generic.content_object == example
