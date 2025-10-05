from __future__ import annotations

from typing import NamedTuple

import pytest
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db.models import CharField, DateField
from django.db.models.functions import Upper

from example_project.app.models import AcceptanceCriteria, Comment, Project, Report, Task, Team
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import parametrize_helper
from undine.dataclasses import BulkCreateKwargs
from undine.exceptions import GraphQLModelNotFoundError, ModelFieldDoesNotExistError, ModelFieldNotARelationError
from undine.utils.model_utils import (
    determine_output_field,
    generic_foreign_key_for_generic_relation,
    generic_relations_for_generic_foreign_key,
    get_bulk_create_kwargs,
    get_bulk_create_update_fields,
    get_instance_or_raise,
    get_instances_or_raise,
    get_model,
    get_model_field,
    get_model_fields_for_graphql,
    get_save_update_fields,
    get_validation_error_messages,
    is_to_many,
    is_to_one,
    lookup_to_display_name,
)

pytestmark = [
    pytest.mark.django_db,
]


def test_get_model_field__same_model() -> None:
    field = get_model_field(model=Project, lookup="name")
    assert field == Project._meta.get_field("name")


def test_get_model_field__related_model() -> None:
    field = get_model_field(model=Project, lookup="team__name")
    assert field == Team._meta.get_field("name")


def test_get_model_field__deep_related_model() -> None:
    field = get_model_field(model=Task, lookup="project__team__name")
    assert field == Team._meta.get_field("name")


def test_get_model_field__pk() -> None:
    field = get_model_field(model=Project, lookup="pk")
    assert field == Project._meta.get_field("id")


def test_get_model_field__related_model_pk() -> None:
    field = get_model_field(model=Project, lookup="team__pk")
    assert field == Team._meta.get_field("id")


def test_get_model_field__field_doesnt_exist() -> None:
    with pytest.raises(ModelFieldDoesNotExistError):
        get_model_field(model=Project, lookup="foo")


def test_get_model_field__no_lookup() -> None:
    with pytest.raises(ModelFieldDoesNotExistError):
        get_model_field(model=Project, lookup="")


def test_get_model_field__not_a_relation() -> None:
    with pytest.raises(ModelFieldNotARelationError):
        get_model_field(model=Project, lookup="id__name")


def test_get_model_field__default_related_name() -> None:
    # Default related name for reverse foreign key and many-to-many relations contains "_set" suffix,
    # but not when asked from model meta fields.
    field = get_model_field(model=Task, lookup="acceptancecriteria_set__details")
    assert field == AcceptanceCriteria._meta.get_field("details")


def test_get_model_field__not_default_related_name() -> None:
    # If related name is overriden, then removing the "_set" suffix doesn't work.
    with pytest.raises(ModelFieldDoesNotExistError):
        get_model_field(model=Task, lookup="taskstep_set__name")


@pytest.mark.django_db
def test_get_instance_or_raise() -> None:
    project = ProjectFactory.create()

    instance = get_instance_or_raise(model=Project, pk=project.pk)
    assert instance == project


@pytest.mark.django_db
def test_get_instance_or_raise__missing() -> None:
    with pytest.raises(GraphQLModelNotFoundError):
        get_instance_or_raise(model=Project, pk=1)


@pytest.mark.django_db
def test_get_instances_or_raise() -> None:
    project = ProjectFactory.create()

    instances = get_instances_or_raise(model=Project, pks=[project.pk])
    assert instances == [project]


@pytest.mark.django_db
def test_get_instances_or_raise__missing() -> None:
    with pytest.raises(GraphQLModelNotFoundError):
        get_instances_or_raise(model=Project, pks=[1])


def test_generic_relations_for_generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")
    relations = list(generic_relations_for_generic_foreign_key(field))

    assert relations == [
        Project._meta.get_field("comments"),
        Task._meta.get_field("comments"),
        Report._meta.get_field("comments"),
    ]


def test_generic_foreign_key_for_generic_relation() -> None:
    field: GenericRelation = Project._meta.get_field("comments")
    generic = generic_foreign_key_for_generic_relation(field)

    assert generic == Comment._meta.get_field("target")


def test_get_model() -> None:
    assert get_model(name="Task") == Task


def test_get_model__with_app_label() -> None:
    assert get_model(name="Task", app_label="app") == Task


def test_get_model__not_found() -> None:
    assert get_model(name="Task", app_label="foo") is None


def test_get_model_fields_for_graphql() -> None:
    fields = sorted(get_model_fields_for_graphql(Task), key=lambda f: f.name)

    assert fields == [
        Task._meta.get_field("acceptancecriteria"),
        Task._meta.get_field("assignees"),
        Task._meta.get_field("attachment"),
        Task._meta.get_field("check_time"),
        Task._meta.get_field("comments"),
        Task._meta.get_field("contact_email"),
        Task._meta.get_field("created_at"),
        Task._meta.get_field("demo_url"),
        Task._meta.get_field("done"),
        Task._meta.get_field("due_by"),
        Task._meta.get_field("external_uuid"),
        Task._meta.get_field("extra_data"),
        Task._meta.get_field("id"),
        Task._meta.get_field("image"),
        Task._meta.get_field("name"),
        Task._meta.get_field("objective"),
        Task._meta.get_field("points"),
        Task._meta.get_field("progress"),
        Task._meta.get_field("project"),
        Task._meta.get_field("related_tasks"),
        Task._meta.get_field("reports"),
        Task._meta.get_field("request"),
        Task._meta.get_field("result"),
        Task._meta.get_field("steps"),
        Task._meta.get_field("type"),
        Task._meta.get_field("worked_hours"),
    ]


def test_get_model_fields_for_graphql__exclude_nonsaveable() -> None:
    fields = sorted(get_model_fields_for_graphql(Task, exclude_nonsaveable=True), key=lambda f: f.name)

    assert fields == [
        Task._meta.get_field("acceptancecriteria"),
        Task._meta.get_field("assignees"),
        Task._meta.get_field("attachment"),
        Task._meta.get_field("check_time"),
        Task._meta.get_field("comments"),
        Task._meta.get_field("contact_email"),
        Task._meta.get_field("demo_url"),
        Task._meta.get_field("done"),
        Task._meta.get_field("due_by"),
        Task._meta.get_field("external_uuid"),
        Task._meta.get_field("extra_data"),
        Task._meta.get_field("id"),
        Task._meta.get_field("image"),
        Task._meta.get_field("name"),
        Task._meta.get_field("objective"),
        Task._meta.get_field("points"),
        Task._meta.get_field("progress"),
        Task._meta.get_field("project"),
        Task._meta.get_field("related_tasks"),
        Task._meta.get_field("reports"),
        Task._meta.get_field("request"),
        Task._meta.get_field("result"),
        Task._meta.get_field("steps"),
        Task._meta.get_field("type"),
        Task._meta.get_field("worked_hours"),
    ]


@pytest.mark.django_db
def test_get_save_update_fields() -> None:
    task = TaskFactory.create()

    assert get_save_update_fields(task, "name") == {"name"}


@pytest.mark.django_db
def test_get_save_update_fields__pk() -> None:
    task = TaskFactory.create()

    assert get_save_update_fields(task, "pk") is None


@pytest.mark.django_db
def test_get_save_update_fields__non_concrete_field() -> None:
    task = TaskFactory.create()

    assert get_save_update_fields(task, "assignees") is None


def test_get_save_update_fields__new_instance() -> None:
    assert get_save_update_fields(Task()) is None


def test_get_bulk_create_update_fields() -> None:
    assert get_bulk_create_update_fields(Task, "name") == {"name"}


def test_get_bulk_create_update_fields__pk() -> None:
    assert get_bulk_create_update_fields(Task, "pk") is None


def test_get_bulk_create_update_fields__non_concrete_field() -> None:
    assert get_bulk_create_update_fields(Task, "assignees") is None


def test_get_bulk_create_kwargs() -> None:
    assert get_bulk_create_kwargs(Task, "name") == BulkCreateKwargs(update_fields={"name"})


def test_get_bulk_create_kwargs__non_concrete_field() -> None:
    assert get_bulk_create_kwargs(Task, "assignees") == BulkCreateKwargs()


def test_determine_output_field() -> None:
    expression = Upper("name")
    output_field = determine_output_field(expression, model=Task)
    assert output_field.__class__.__name__ == "CharField"


def test_is_to_one() -> None:
    assert is_to_one(Task._meta.get_field("name")) is False
    assert is_to_one(Task._meta.get_field("request")) is True
    assert is_to_one(Task._meta.get_field("project")) is True
    assert is_to_one(Task._meta.get_field("assignees")) is False
    assert is_to_one(Task._meta.get_field("comments")) is False
    assert is_to_one(Task._meta.get_field("result")) is True
    assert is_to_one(Task._meta.get_field("steps")) is False
    assert is_to_one(Task._meta.get_field("reports")) is False


def test_is_to_many() -> None:
    assert is_to_many(Task._meta.get_field("name")) is False
    assert is_to_many(Task._meta.get_field("request")) is False
    assert is_to_many(Task._meta.get_field("project")) is False
    assert is_to_many(Task._meta.get_field("assignees")) is True
    assert is_to_many(Task._meta.get_field("comments")) is True
    assert is_to_many(Task._meta.get_field("result")) is False
    assert is_to_many(Task._meta.get_field("steps")) is True
    assert is_to_many(Task._meta.get_field("reports")) is True


class Params(NamedTuple):
    lookup: str
    display_name: str


@pytest.mark.parametrize(
    **parametrize_helper({
        "exact": Params(
            lookup="exact",
            display_name="",
        ),
        "startswith": Params(
            lookup="startswith",
            display_name="starts_with",
        ),
        "endswith": Params(
            lookup="endswith",
            display_name="ends_with",
        ),
        "contains": Params(
            lookup="contains",
            display_name="contains",
        ),
        "isnull": Params(
            lookup="isnull",
            display_name="is_null",
        ),
        "isempty": Params(
            lookup="isempty",
            display_name="is_empty",
        ),
        "with transform": Params(
            lookup="date__contains",
            display_name="date_contains",
        ),
        "with transform exact": Params(
            lookup="date__exact",
            display_name="date",
        ),
    })
)
def test_lookup_to_display_name(lookup, display_name) -> None:
    assert lookup_to_display_name(lookup, DateField()) == display_name


@pytest.mark.parametrize(
    **parametrize_helper({
        "exact": Params(
            lookup="exact",
            display_name="exact",
        ),
        "iexact": Params(
            lookup="iexact",
            display_name="",
        ),
        "startswith": Params(
            lookup="startswith",
            display_name="starts_with_exact",
        ),
        "istartswith": Params(
            lookup="istartswith",
            display_name="starts_with",
        ),
        "endswith": Params(
            lookup="endswith",
            display_name="ends_with_exact",
        ),
        "iendswith": Params(
            lookup="iendswith",
            display_name="ends_with",
        ),
        "contains": Params(
            lookup="contains",
            display_name="contains_exact",
        ),
        "icontains": Params(
            lookup="icontains",
            display_name="contains",
        ),
        "with transform": Params(
            lookup="date__icontains",
            display_name="date_contains",
        ),
        "with transform iexact": Params(
            lookup="date__iexact",
            display_name="date",
        ),
    })
)
def test_lookup_to_display_name__text_field(lookup, display_name) -> None:
    assert lookup_to_display_name(lookup, CharField()) == display_name


class ValidationErrorTestParams(NamedTuple):
    error: ValidationError
    output: dict[str, list[str]]


@pytest.mark.parametrize(
    **parametrize_helper({
        "one error": ValidationErrorTestParams(
            error=ValidationError("foo"),
            output={"": ["foo"]},
        ),
        "two errors": ValidationErrorTestParams(
            error=ValidationError(["foo", "bar"]),
            output={"": ["foo", "bar"]},
        ),
        "keyed error": ValidationErrorTestParams(
            error=ValidationError({"foo": "bar"}),
            output={"foo": ["bar"]},
        ),
        "two keyed errors": ValidationErrorTestParams(
            error=ValidationError({"foo": "bar", "fizz": "buzz"}),
            output={"foo": ["bar"], "fizz": ["buzz"]},
        ),
        "two keyed errors list": ValidationErrorTestParams(
            error=ValidationError({"foo": ["bar", "baz"]}),
            output={"foo": ["bar", "baz"]},
        ),
        "nested": ValidationErrorTestParams(
            error=ValidationError({"foo": [ValidationError("bar")]}),
            output={"foo": ["bar"]},
        ),
        "nested multiple": ValidationErrorTestParams(
            error=ValidationError({"foo": [ValidationError("bar"), ValidationError("baz")]}),
            output={"foo": ["bar", "baz"]},
        ),
        "nested list": ValidationErrorTestParams(
            error=ValidationError({"foo": [ValidationError([ValidationError("baz")])]}),
            output={"foo": ["baz"]},
        ),
        "nested dicts": ValidationErrorTestParams(
            # ValidationError doesn't retain key for the second level dicts.
            error=ValidationError({"foo": [ValidationError({"bar": ValidationError("baz")})]}),
            output={"foo": ["baz"]},
        ),
        "params": ValidationErrorTestParams(
            error=ValidationError("%(foo)s", params={"foo": "bar"}),
            output={"": ["bar"]},
        ),
        "params nested": ValidationErrorTestParams(
            error=ValidationError({"foo": [ValidationError("%(foo)s", params={"foo": "bar"})]}),
            output={"foo": ["bar"]},
        ),
    })
)
def test_get_validation_error_messages(error, output) -> None:
    assert get_validation_error_messages(error) == output
