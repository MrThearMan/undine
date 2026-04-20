from __future__ import annotations

from typing import NamedTuple
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db.models import CharField, DateField, F, Value
from django.db.models.fields.related import ManyToManyRel
from django.db.models.functions import Upper
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.db.utils import IntegrityError

from example_project.app.models import AcceptanceCriteria, Comment, Project, Report, Task, Team
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import parametrize_helper
from undine.dataclasses import BulkCreateKwargs
from undine.exceptions import (
    ExpressionMultipleOutputFieldError,
    ExpressionNoOutputFieldError,
    GraphQLDuplicatePrimaryKeysError,
    GraphQLModelConstraintViolationError,
    GraphQLModelNotFoundError,
    GraphQLModelsNotFoundError,
    GraphQLPrimaryKeysMissingError,
    ModelFieldDoesNotExistError,
    ModelFieldNotARelationError,
)
from undine.utils.model_utils import (
    SubqueryCount,
    convert_integrity_errors,
    create_union_queryset,
    determine_output_field,
    generic_foreign_key_for_generic_relation,
    generic_relations_for_generic_foreign_key,
    get_bulk_create_kwargs,
    get_bulk_create_update_fields,
    get_db_features,
    get_field_name,
    get_instance_or_raise,
    get_instances_or_raise,
    get_many_to_many_through_field,
    get_model,
    get_model_field,
    get_model_fields_for_graphql,
    get_pks_from_list_of_dicts,
    get_related_query_name,
    get_save_update_fields,
    get_validation_error_messages,
    has_default,
    is_generic_foreign_key,
    is_to_many,
    is_to_one,
    lookup_to_display_name,
    set_forward_ids,
    use_delete_signals,
    use_m2m_add_signals,
    use_m2m_remove_signals,
    use_save_signals,
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


def test_get_instances_or_raise__multiple_missing() -> None:
    with pytest.raises(GraphQLModelsNotFoundError):
        get_instances_or_raise(model=Project, pks=[1, 2])


def test_get_pks_from_list_of_dicts() -> None:
    result = get_pks_from_list_of_dicts([{"pk": 1}, {"pk": 2}])
    assert result == [1, 2]


def test_get_pks_from_list_of_dicts__missing_pk() -> None:
    with pytest.raises(GraphQLPrimaryKeysMissingError):
        get_pks_from_list_of_dicts([{"pk": 1}, {"name": "no pk"}])


def test_get_pks_from_list_of_dicts__duplicate_pks() -> None:
    with pytest.raises(GraphQLDuplicatePrimaryKeysError):
        get_pks_from_list_of_dicts([{"pk": 1}, {"pk": 1}])


def test_get_model__not_found_no_app_label() -> None:
    result = get_model(name="NonExistentModel999")
    assert result is None


def test_get_many_to_many_through_field__forward() -> None:
    field = Task._meta.get_field("assignees")
    result = get_many_to_many_through_field(field)
    assert result is not None


def test_get_many_to_many_through_field__reverse() -> None:
    field = Task._meta.get_field("assignees")
    rel: ManyToManyRel = field.remote_field
    result = get_many_to_many_through_field(rel)
    assert result is not None


def test_get_related_query_name__callable() -> None:
    field = Task._meta.get_field("acceptancecriteria")
    # Test that we get a string result regardless of whether it's callable or not
    result = get_related_query_name(field)
    assert isinstance(result, str)


def test_get_related_query_name__callable_method() -> None:
    class MockFieldWithCallable:
        name = "field"

        @property
        def related_query_name(self):
            return lambda: "query_name"

    result = get_related_query_name(MockFieldWithCallable())
    assert result == "query_name"


def test_get_field_name() -> None:
    field = Task._meta.get_field("project")
    assert get_field_name(field) == "project"


def test_get_related_query_name__non_callable() -> None:
    class MockField:
        related_query_name = "query_name"
        name = "field"

    result = get_related_query_name(MockField())
    assert result == "query_name"


def test_get_related_query_name__no_attr() -> None:
    class MockField:
        name = "field"

    result = get_related_query_name(MockField())
    assert result == "field"


def test_is_generic_foreign_key__true() -> None:
    field = Comment._meta.get_field("target")
    assert is_generic_foreign_key(field) is True


def test_is_generic_foreign_key__false() -> None:
    field = Task._meta.get_field("project")
    assert is_generic_foreign_key(field) is False


def test_has_default__auto_now() -> None:
    field = Task._meta.get_field("created_at")
    assert has_default(field) is True


def test_has_default__no_default() -> None:
    field = Task._meta.get_field("name")
    assert has_default(field) is False


def test_use_save_signals__no_listeners() -> None:
    project = Project(name="Test")
    with use_save_signals(Project, [project], update_fields=None):
        pass  # just verify no error


def test_use_delete_signals__no_listeners() -> None:
    project = Project(name="Test")
    with use_delete_signals(Project, [project]):
        pass  # just verify no error


def test_use_m2m_signals__no_listeners() -> None:
    task = TaskFactory.build()
    task.pk = 998
    with use_m2m_remove_signals(Task, {task: {1}}, target_name="assignees", reverse=False):
        pass

    with use_m2m_add_signals(Task, {task: {1}}, target_name="assignees", reverse=False):
        pass


def test_use_save_signals() -> None:
    received = []

    def handler(sender, instance, **kwargs):
        received.append((sender, instance))

    pre_save.connect(handler, sender=Project)
    post_save.connect(handler, sender=Project)

    project = Project(name="Test")
    try:
        with use_save_signals(Project, [project], update_fields=None):
            pass
    finally:
        pre_save.disconnect(handler, sender=Project)
        post_save.disconnect(handler, sender=Project)

    assert len(received) == 2


def test_use_delete_signals() -> None:
    received = []

    def handler(sender, instance, **kwargs):
        received.append((sender, instance))

    pre_delete.connect(handler, sender=Project)
    post_delete.connect(handler, sender=Project)

    project = Project(name="Test")
    try:
        with use_delete_signals(Project, [project]):
            pass
    finally:
        pre_delete.disconnect(handler, sender=Project)
        post_delete.disconnect(handler, sender=Project)

    assert len(received) == 2


def test_use_m2m_remove_signals() -> None:
    received = []

    def handler(sender, action, **kwargs):
        received.append(action)

    m2m_changed.connect(handler, sender=Task)

    task = TaskFactory.build()
    task.pk = 999
    try:
        with use_m2m_remove_signals(Task, {task: {1}}, target_name="assignees", reverse=False):
            pass
    finally:
        m2m_changed.disconnect(handler, sender=Task)

    assert "pre_remove" in received
    assert "post_remove" in received


def test_use_m2m_add_signals() -> None:
    received = []

    def handler(sender, action, **kwargs):
        received.append(action)

    m2m_changed.connect(handler, sender=Task)

    task = TaskFactory.build()
    task.pk = 999
    try:
        with use_m2m_add_signals(Task, {task: {1}}, target_name="assignees", reverse=False):
            pass
    finally:
        m2m_changed.disconnect(handler, sender=Task)

    assert "pre_add" in received
    assert "post_add" in received


def test_determine_output_field__sub_expressions() -> None:
    # ExpressionWrapper without output_field at creation time but with sub-expressions
    # that have output_field
    inner = Value(1)
    expr = inner + Value(2)
    output_field = determine_output_field(expr, model=Task)
    assert output_field is not None


def test_determine_output_field__with_f_expression() -> None:
    # Use a combination expression where one sub-expr is F
    class ExprWithoutOutputField:
        def get_source_expressions(self):
            return [F("name")]

    expr = ExprWithoutOutputField()
    output_field = determine_output_field(expr, model=Task)
    assert output_field is not None


def test_determine_output_field__sub_expr_no_output_field_no_f() -> None:
    class UnknownExpr:
        pass

    class ExprWithUnknownSource:
        def get_source_expressions(self):
            return [UnknownExpr()]

    expr = ExprWithUnknownSource()
    # This should skip the expr since it has no output_field and is not F
    # ExpressionNoOutputFieldError since no fields collected
    with pytest.raises(Exception):  # noqa: PT011,B017
        determine_output_field(expr, model=Task)


def test_determine_output_field__no_output_fields() -> None:
    class ExprWithNoSources:
        def get_source_expressions(self):
            return []

    expr = ExprWithNoSources()
    with pytest.raises(ExpressionNoOutputFieldError):
        determine_output_field(expr, model=Task)


def test_determine_output_field__multiple_output_fields() -> None:
    class ExprWithMultipleSources:
        def get_source_expressions(self):
            return [Value("text"), Value(1)]

    expr = ExprWithMultipleSources()
    with pytest.raises(ExpressionMultipleOutputFieldError):
        determine_output_field(expr, model=Task)


def test_set_forward_ids__with_generic_fk() -> None:
    comment = Comment(object_id="1")
    set_forward_ids(comment)  # should not error


def test_create_union_queryset() -> None:
    qs1 = Task.objects.filter(pk=1)
    qs2 = Task.objects.filter(pk=2)
    result = create_union_queryset([qs1, qs2])
    assert result is not None


def test_get_db_features() -> None:
    features = get_db_features()
    assert features is not None


def test_create_union_queryset__no_reorder() -> None:
    get_db_features()
    features_with_support = type("F", (), {"supports_slicing_ordering_in_compound": True})()

    with patch("undine.utils.model_utils.get_db_features", return_value=features_with_support):
        qs1 = Task.objects.filter(pk=1)
        qs2 = Task.objects.filter(pk=2)
        result = create_union_queryset([qs1, qs2])
        assert result is not None


def test_subquery_count__repr__exception() -> None:
    qs = Task.objects.all()
    sq = SubqueryCount(qs)

    class BrokenQuery:
        def __str__(self):
            msg = "broken"
            raise ValueError(msg)

    sq.query = BrokenQuery()
    result = repr(sq)
    assert "<subquery>" in result


def test_set_forward_ids() -> None:
    task = Task(name="Test")
    set_forward_ids(task)  # just verify no error


def test_convert_integrity_errors() -> None:
    msg = "UNIQUE constraint failed: app_task.name"
    with pytest.raises(GraphQLModelConstraintViolationError), convert_integrity_errors():
        raise IntegrityError(msg)
