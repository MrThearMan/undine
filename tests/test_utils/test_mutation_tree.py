from __future__ import annotations

import datetime

import pytest
from django.contrib.contenttypes.models import ContentType

from example_project.app.models import Comment, ServiceRequest, Task, TaskResult, TaskStep, TaskTypeChoices
from example_project.example.models import Example, ExampleGeneric
from pytest_undine.query_logging import capture_database_queries
from tests.factories import PersonFactory, TaskFactory, TaskResultFactory, TaskStepFactory, TeamFactory
from tests.factories.example import (
    ExampleFactory,
    ExampleFFKFactory,
    ExampleFMTMFactory,
    ExampleFOTOFactory,
    ExampleRFKFactory,
    ExampleRMTMFactory,
    ExampleROTOFactory,
)
from undine.dataclasses import RelInfo
from undine.exceptions import (
    GraphQLInvalidInputDataError,
    GraphQLMutationTreeModelMismatchError,
    GraphQLRelationMultipleInstancesError,
    GraphQLRelationNotNullableError,
)
from undine.typing import RelatedAction, RelationType
from undine.utils.mutation_tree import MutationNode, mutate


@pytest.mark.django_db
def test_mutation_optimization(undine_settings) -> None:  # noqa: C901, PLR0912
    undine_settings.MUTATION_FULL_CLEAN = False
    undine_settings.MUTATION_INSTANCE_LIMIT = 200

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
        example = mutate(model=Example, data=data)

    assert queries.count == 88, queries.log

    example.refresh_from_db()

    assert example.pk == ex.pk
    assert example.name == "foo"

    # example_foto
    assert example.example_foto is not None
    assert example.example_foto.name == "foo"

    assert example.example_foto.example_foto is not None
    assert example.example_foto.example_foto.name == "foo"

    assert example.example_foto.example_ffk is not None
    assert example.example_foto.example_ffk.name == "foo"

    assert example.example_foto.example_roto is not None
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
    assert example.example_ffk is not None
    assert example.example_ffk.name == "foo"

    assert example.example_ffk.example_foto is not None
    assert example.example_ffk.example_foto.name == "foo"

    assert example.example_ffk.example_ffk is not None
    assert example.example_ffk.example_ffk.name == "foo"

    assert example.example_ffk.example_roto is not None
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
    assert example.example_roto is not None
    assert example.example_roto.name == "foo"

    assert example.example_roto.example_foto is not None
    assert example.example_roto.example_foto.name == "foo"

    assert example.example_roto.example_ffk is not None
    assert example.example_roto.example_ffk.name == "foo"

    assert example.example_roto.example_roto is not None
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

        assert example_fmtm.example_foto is not None
        assert example_fmtm.example_foto.name == "foo"

        assert example_fmtm.example_ffk is not None
        assert example_fmtm.example_ffk.name == "foo"

        assert example_fmtm.example_roto is not None
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

        assert example_rfk.example_foto is not None
        assert example_rfk.example_foto.name == "foo"

        assert example_rfk.example_ffk is not None
        assert example_rfk.example_ffk.name == "foo"

        assert example_rfk.example_roto is not None
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

        assert example_rmtm.example_foto is not None
        assert example_rmtm.example_foto.name == "foo"

        assert example_rmtm.example_ffk is not None
        assert example_rmtm.example_ffk.name == "foo"

        assert example_rmtm.example_roto is not None
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
        example = mutate(model=Example, data=data)

    assert queries.count == 15, queries.log

    example.refresh_from_db()

    assert example.name == "foo"

    assert example.example_foto is not None
    assert example.example_foto.pk == example_foto.pk

    assert example.example_ffk is not None
    assert example.example_ffk.pk == example_ffk.pk

    assert example.example_roto is not None
    assert example.example_roto.pk == example_roto.pk

    example_fmtm_set = list(example.example_fmtm_set.all())
    assert len(example_fmtm_set) == 1
    assert example_fmtm_set[0].pk == example_fmtm.pk

    example_rfk_set = list(example.example_rfk_set.all())
    assert len(example_rfk_set) == 1
    assert example_rfk_set[0].pk == example_rfk.pk

    example_rmtm_set = list(example.example_rmtm_set.all())
    assert len(example_rmtm_set) == 1
    assert example_rmtm_set[0].pk == example_rmtm.pk


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
        example = mutate(model=Example, data=data)

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
        example = mutate(model=Example, data=data)

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
        example = mutate(model=Example, data=data)

    assert queries.count == 20, queries.log

    example.refresh_from_db()

    assert example.name == "bar"

    assert example.example_foto is not None
    assert example.example_foto.name == "bar"

    assert example.example_ffk is not None
    assert example.example_ffk.name == "bar"

    assert example.example_roto is not None
    assert example.example_roto.name == "bar"

    example_fmtm_set = list(example.example_fmtm_set.all())
    assert len(example_fmtm_set) == 1
    assert example_fmtm_set[0].name == "bar"

    example_rfk_set = list(example.example_rfk_set.all())
    assert len(example_rfk_set) == 1
    assert example_rfk_set[0].name == "bar"

    example_rmtm_set = list(example.example_rmtm_set.all())
    assert len(example_rmtm_set) == 1
    assert example_rmtm_set[0].name == "bar"


@pytest.mark.django_db
def test_mutation_optimization__different_contents(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    example_fmtm = ExampleFMTMFactory.create(name="foo")
    example = ExampleFactory.create(example_fmtm_set=[example_fmtm])

    data = {
        "pk": example.pk,
        "example_fmtm_set": [
            {"pk": example_fmtm.pk},
            {"name": "bar"},
        ],
    }

    with capture_database_queries() as queries:
        example = mutate(model=Example, data=data)

    assert queries.count == 8, queries.log

    example.refresh_from_db()

    example_fmtm_set = list(example.example_fmtm_set.all())
    assert len(example_fmtm_set) == 2

    assert example_fmtm_set[0].pk == example_fmtm.pk
    assert example_fmtm_set[0].name == "foo"

    assert example_fmtm_set[1].name == "bar"


@pytest.mark.django_db
def test_mutation_optimization__create_symmetrical(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    existing_example = ExampleFactory.create(name="foo")

    data = {
        "name": "bar",
        "symmetrical_field": [existing_example.pk],
    }

    with capture_database_queries() as queries:
        new_example = mutate(model=Example, data=data)

    assert queries.count == 5, queries.log

    assert new_example.name == "bar"

    symmetrical_field = list(new_example.symmetrical_field.all())
    assert len(symmetrical_field) == 1
    assert symmetrical_field[0].name == "foo"

    existing_example.refresh_from_db()

    assert existing_example.name == "foo"

    symmetrical_field = list(existing_example.symmetrical_field.all())
    assert len(symmetrical_field) == 1
    assert symmetrical_field[0].name == "bar"


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
        new_example = mutate(model=Example, data=data)

    assert queries.count == 5, queries.log

    assert new_example.name == "baz"

    symmetrical_field = list(new_example.symmetrical_field.all())
    assert len(symmetrical_field) == 1
    assert symmetrical_field[0].name == "foo"

    example_1.refresh_from_db()
    assert example_1.name == "foo"

    symmetrical_field = list(example_1.symmetrical_field.all())
    assert len(symmetrical_field) == 2
    assert symmetrical_field[0].name == "bar"
    assert symmetrical_field[1].name == "baz"

    example_2.refresh_from_db()
    assert example_2.name == "bar"

    symmetrical_field = list(example_2.symmetrical_field.all())
    assert len(symmetrical_field) == 1
    assert symmetrical_field[0].name == "foo"


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
        mutate(model=Example, data=data)

    assert queries.count == 3, queries.log

    example_1.refresh_from_db()
    assert example_1.symmetrical_field.count() == 0

    example_2.refresh_from_db()
    assert example_2.symmetrical_field.count() == 0


@pytest.mark.django_db
def test_mutation_optimization__generic_relation(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # Cache the content type
    ContentType.objects.get_for_model(Example)

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
        example = mutate(model=Example, data=data)

    assert queries.count == 2, queries.log

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
        example_generic = mutate(model=ExampleGeneric, data=data)

    assert queries.count == 2, queries.log

    assert example_generic.name == "bar"

    assert example_generic.content_object is not None
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
        example_generic = mutate(model=ExampleGeneric, data=data)

    assert queries.count == 2, queries.log

    assert example_generic.name == "bar"

    assert example_generic.content_object is not None
    assert example_generic.content_object == example


@pytest.mark.django_db
def test_mutation__forward_o2o__none__not_nullable(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    rel_info = RelInfo(
        relation_type=RelationType.FORWARD_ONE_TO_ONE,
        field_name="request",
        model=Task,
        model_pk_type=int,
        nullable=False,
        related_name="task",
        related_model=Task,
        related_model_pk_type=int,
        related_nullable=False,
    )
    node = MutationNode(model=Task, related_action=RelatedAction.null)
    instance = Task()

    with pytest.raises(GraphQLRelationNotNullableError):
        node._handle_forward_o2o(None, rel_info, instance, MutationNode(model=Task))


@pytest.mark.django_db
def test_mutation__forward_o2o__invalid_data(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    rel_info = RelInfo(
        relation_type=RelationType.FORWARD_ONE_TO_ONE,
        field_name="request",
        model=Task,
        model_pk_type=int,
        nullable=True,
        related_name="task",
        related_model=Task,
        related_model_pk_type=int,
        related_nullable=True,
    )
    node = MutationNode(model=Task, related_action=RelatedAction.null)
    instance = Task()

    with pytest.raises(GraphQLInvalidInputDataError):
        node._handle_forward_o2o([1, 2, 3], rel_info, instance, MutationNode(model=Task))


@pytest.mark.django_db
def test_mutation__reverse_o2o__invalid_data(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    rel_info = RelInfo(
        relation_type=RelationType.REVERSE_ONE_TO_ONE,
        field_name="result",
        model=Task,
        model_pk_type=int,
        nullable=True,
        related_name="task",
        related_model=TaskResult,
        related_model_pk_type=int,
        related_nullable=True,
    )
    node = MutationNode(model=Task, related_action=RelatedAction.null)
    instance = Task()

    with pytest.raises(GraphQLInvalidInputDataError):
        node._handle_reverse_o2o([1, 2, 3], rel_info, instance, MutationNode(model=TaskResult))


@pytest.mark.django_db
def test_mutation__reverse_o2o__ignore__multiple_instances(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    existing_result = TaskResultFactory.create()
    task = existing_result.task

    data = {
        "pk": task.pk,
        "result": {"details": "new result", "time_used": None},
    }

    with pytest.raises(GraphQLRelationMultipleInstancesError):
        mutate(model=Task, data=data, related_action=RelatedAction.ignore)


@pytest.mark.django_db
def test_mutation__o2m__invalid_data(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    rel_info = RelInfo(
        relation_type=RelationType.REVERSE_ONE_TO_MANY,
        field_name="steps",
        model=Task,
        model_pk_type=int,
        nullable=True,
        related_name="task",
        related_model=TaskStep,
        related_model_pk_type=int,
        related_nullable=False,
    )
    node = MutationNode(model=Task, related_action=RelatedAction.null)
    instance = Task()

    with pytest.raises(GraphQLInvalidInputDataError):
        node._handle_o2m("invalid_string", rel_info, instance, MutationNode(model=TaskStep))


@pytest.mark.django_db
def test_mutation__m2m__invalid_data(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    rel_info = RelInfo(
        relation_type=RelationType.FORWARD_MANY_TO_MANY,
        field_name="example_fmtm_set",
        model=Example,
        model_pk_type=int,
        nullable=True,
        related_name="example_set",
        related_model=ExampleGeneric,
        related_model_pk_type=int,
        related_nullable=True,
    )
    node = MutationNode(model=Example, related_action=RelatedAction.null)
    instance = Example()

    with pytest.raises(GraphQLInvalidInputDataError):
        node._handle_m2m("invalid_string", rel_info, instance, MutationNode(model=ExampleGeneric))


@pytest.mark.django_db
def test_mutation__generic_fk__not_dict(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    ContentType.objects.get_for_model(Example)

    with pytest.raises(GraphQLInvalidInputDataError):
        mutate(
            model=ExampleGeneric,
            data={
                "name": "bar",
                "content_object": 123,
            },
        )


@pytest.mark.django_db
def test_mutation__generic_fk__empty_dict(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    ContentType.objects.get_for_model(Example)

    with pytest.raises(GraphQLInvalidInputDataError):
        mutate(
            model=ExampleGeneric,
            data={
                "name": "bar",
                "content_object": {},
            },
        )


@pytest.mark.django_db
def test_mutation__generic_fk__unknown_model(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    ContentType.objects.get_for_model(Example)

    with pytest.raises(GraphQLInvalidInputDataError):
        mutate(
            model=ExampleGeneric,
            data={
                "name": "bar",
                "content_object": {"UnknownModel": {"name": "foo"}},
            },
        )


@pytest.mark.django_db
def test_mutation__generic_fk__null_value(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    ContentType.objects.get_for_model(Task)

    comment = mutate(
        model=Comment,
        data={
            "contents": "test comment",
            "target": {"task": None},
        },
    )

    comment.refresh_from_db()
    assert comment.contents == "test comment"
    assert comment.target is None


@pytest.mark.django_db
def test_mutation__generic_fk__invalid_model_data(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    ContentType.objects.get_for_model(Task)

    with pytest.raises(GraphQLInvalidInputDataError):
        mutate(
            model=Comment,
            data={
                "contents": "test comment",
                "target": {"task": 123},
            },
        )


@pytest.mark.django_db
def test_mutation__merge__model_mismatch(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    task_node = MutationNode(model=Task)
    step_node = MutationNode(model=TaskStep)

    with pytest.raises(GraphQLMutationTreeModelMismatchError):
        task_node.merge(step_node)


@pytest.mark.django_db
def test_mutation__merge__before_and_after_nodes(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    team = TeamFactory.create(name="team")

    data = [
        {
            "name": "task1",
            "type": TaskTypeChoices.TASK,
            "project": {"name": "p1", "team": team.pk},
        },
        {
            "name": "task2",
            "type": TaskTypeChoices.TASK,
            "project": {"name": "p2", "team": team.pk},
        },
    ]

    tasks = mutate(model=Task, data=data)

    assert len(tasks) == 2
    assert tasks[0].name == "task1"
    assert tasks[1].name == "task2"
    assert tasks[0].project is not None
    assert tasks[1].project is not None


@pytest.mark.django_db
def test_mutation__forward_o2o__instance(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    request = ServiceRequest(details="Test request")
    request.save()

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.TASK,
        "request": request,
    }

    task = mutate(model=Task, data=data)
    task.refresh_from_db()

    assert task.request == request


@pytest.mark.django_db
def test_mutation__reverse_o2o__instance(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    task = TaskFactory.create()
    result = TaskResult(task=task, details="result", time_used=datetime.timedelta(seconds=10))
    result.save()

    task.refresh_from_db()
    data = {
        "pk": task.pk,
        "result": result,
    }

    updated_task = mutate(model=Task, data=data)
    updated_task.refresh_from_db()

    assert updated_task.result == result


@pytest.mark.django_db
def test_mutation__reverse_o2o__delete(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    task = TaskFactory.create()
    existing_result = TaskResult(task=task, details="old result", time_used=datetime.timedelta(seconds=5))
    existing_result.save()

    task.refresh_from_db()
    data = {
        "pk": task.pk,
        "result": {"details": "new result", "time_used": datetime.timedelta(seconds=10)},
    }

    updated_task = mutate(model=Task, data=data, related_action=RelatedAction.delete)
    updated_task.refresh_from_db()

    assert updated_task.result is not None
    assert updated_task.result.details == "new result"
    assert not TaskResult.objects.filter(pk=existing_result.pk).exists()


@pytest.mark.django_db
def test_mutation__o2m__instance(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    task = TaskFactory.create()
    step = TaskStepFactory.create()

    data = {
        "pk": task.pk,
        "steps": [step],
    }

    updated_task = mutate(model=Task, data=data)
    updated_task.refresh_from_db()

    assert list(updated_task.steps.all()) == [step]


@pytest.mark.django_db
def test_mutation__o2m__delete(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    task = TaskFactory.create()
    existing_step = TaskStepFactory.create(task=task)

    data = {
        "pk": task.pk,
        "steps": [{"name": "new step"}],
    }

    updated_task = mutate(model=Task, data=data, related_action=RelatedAction.delete)
    updated_task.refresh_from_db()

    assert updated_task.steps.count() == 1
    assert not TaskStep.objects.filter(pk=existing_step.pk).exists()


@pytest.mark.django_db
def test_mutation__m2m__instance(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    person = PersonFactory.create()

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.TASK,
        "assignees": [person],
    }

    task = mutate(model=Task, data=data)
    task.refresh_from_db()

    assert list(task.assignees.all()) == [person]


@pytest.mark.django_db
def test_mutation__generic_fk__null_not_nullable(undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    rel_info = RelInfo(
        relation_type=RelationType.GENERIC_MANY_TO_ONE,
        field_name="content_object",
        model=ExampleGeneric,
        model_pk_type=int,
        nullable=False,
        related_name=None,
        related_model=None,
        related_model_pk_type=int,
        related_nullable=False,  # Not nullable
    )
    node = MutationNode(model=ExampleGeneric, related_action=RelatedAction.null)
    instance = ExampleGeneric()

    with pytest.raises(GraphQLRelationNotNullableError):
        node._handle_generic_fk({"example": None}, rel_info, instance, MutationNode(model=Example))
