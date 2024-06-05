from __future__ import annotations

import datetime

from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    EmailField,
    FileField,
    ForeignKey,
    ImageField,
    IntegerField,
    JSONField,
    Model,
    TextChoices,
    TimeField,
    URLField,
    UUIDField,
)

from example_project.app.models import Task
from undine.filtering import get_filters_for_model


class OneRelated(Model):
    name = CharField(max_length=255)

    class Meta:
        managed = False
        app_label = __name__


class ExampleType(TextChoices):
    FOO = "foo", "Foo"
    BAR = "bar", "Bar"


class Example(Model):
    name = CharField(max_length=255)
    type = CharField(choices=ExampleType.choices, max_length=255)
    created_at = DateTimeField(auto_now_add=True)
    done = BooleanField(default=False)
    due_by = DateField(null=True, blank=True)
    check_time = TimeField(null=True, blank=True)
    points = IntegerField(null=True, blank=True)
    progress = DecimalField(default=0, max_digits=3, decimal_places=2)
    worked_hours = DurationField(default=datetime.timedelta)
    contact_email = EmailField(null=True, blank=True)  # noqa: DJ001
    demo_url = URLField(null=True, blank=True)  # noqa: DJ001
    external_uuid = UUIDField(null=True, blank=True)
    extra_data = JSONField(null=True, blank=True)
    image = ImageField(null=True, blank=True)
    attachment = FileField(null=True, blank=True)

    one_relation = ForeignKey(OneRelated, on_delete=CASCADE, related_name="examples")

    class Meta:
        managed = False
        app_label = __name__


def test_get_filters_for_model__exclude() -> None:
    fields = get_filters_for_model(Example, exclude=["name", "created_at_gt"])

    name_field_names = sorted(name for name in fields if name.startswith("name"))
    assert name_field_names == []

    created_at_field_names = sorted(name for name in fields if name.startswith("created_at"))
    assert "created_at_gt" not in created_at_field_names


def test_get_filters_for_model__pk() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    pk_field_names = sorted(name for name in fields if name.startswith("pk"))
    assert pk_field_names == [
        "pk",
        "pk_contains",
        "pk_ends_with",
        "pk_gt",
        "pk_gte",
        "pk_in",
        "pk_lt",
        "pk_lte",
        "pk_range",
        "pk_starts_with",
    ]

    # Actual primary key id not included since PK is
    id_field_names = sorted(name for name in fields if name.startswith("id"))
    assert id_field_names == []


def test_get_filters_for_model__char_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    name_field_names = sorted(name for name in fields if name.startswith("name"))
    assert name_field_names == [
        "name",
        "name_contains",
        "name_contains_exact",
        "name_ends_with",
        "name_ends_with_exact",
        "name_exact",
        "name_in",
        "name_starts_with",
        "name_starts_with_exact",
    ]


def test_get_filters_for_model__char_field__choices() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    type_field_names = sorted(name for name in fields if name.startswith("type"))
    assert type_field_names == [
        "type",
        "type_contains",
        "type_contains_exact",
        "type_ends_with",
        "type_ends_with_exact",
        "type_exact",
        "type_in",
        "type_starts_with",
        "type_starts_with_exact",
    ]


def test_get_filters_for_model__datetime_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    created_at_field_names = sorted(name for name in fields if name.startswith("created_at"))
    assert created_at_field_names == [
        "created_at",
        "created_at_date",
        "created_at_date_gt",
        "created_at_date_gte",
        "created_at_date_in",
        "created_at_date_lt",
        "created_at_date_lte",
        "created_at_date_range",
        "created_at_day",
        "created_at_day_contains",
        "created_at_day_ends_with",
        "created_at_day_gt",
        "created_at_day_gte",
        "created_at_day_in",
        "created_at_day_lt",
        "created_at_day_lte",
        "created_at_day_range",
        "created_at_day_starts_with",
        "created_at_gt",
        "created_at_gte",
        "created_at_hour",
        "created_at_hour_contains",
        "created_at_hour_ends_with",
        "created_at_hour_gt",
        "created_at_hour_gte",
        "created_at_hour_in",
        "created_at_hour_lt",
        "created_at_hour_lte",
        "created_at_hour_range",
        "created_at_hour_starts_with",
        "created_at_in",
        "created_at_iso_week_day",
        "created_at_iso_week_day_contains",
        "created_at_iso_week_day_ends_with",
        "created_at_iso_week_day_gt",
        "created_at_iso_week_day_gte",
        "created_at_iso_week_day_in",
        "created_at_iso_week_day_lt",
        "created_at_iso_week_day_lte",
        "created_at_iso_week_day_range",
        "created_at_iso_week_day_starts_with",
        "created_at_iso_year",
        "created_at_iso_year_contains",
        "created_at_iso_year_ends_with",
        "created_at_iso_year_gt",
        "created_at_iso_year_gte",
        "created_at_iso_year_in",
        "created_at_iso_year_lt",
        "created_at_iso_year_lte",
        "created_at_iso_year_range",
        "created_at_iso_year_starts_with",
        "created_at_lt",
        "created_at_lte",
        "created_at_minute",
        "created_at_minute_contains",
        "created_at_minute_ends_with",
        "created_at_minute_gt",
        "created_at_minute_gte",
        "created_at_minute_in",
        "created_at_minute_lt",
        "created_at_minute_lte",
        "created_at_minute_range",
        "created_at_minute_starts_with",
        "created_at_month",
        "created_at_month_contains",
        "created_at_month_ends_with",
        "created_at_month_gt",
        "created_at_month_gte",
        "created_at_month_in",
        "created_at_month_lt",
        "created_at_month_lte",
        "created_at_month_range",
        "created_at_month_starts_with",
        "created_at_quarter",
        "created_at_quarter_contains",
        "created_at_quarter_ends_with",
        "created_at_quarter_gt",
        "created_at_quarter_gte",
        "created_at_quarter_in",
        "created_at_quarter_lt",
        "created_at_quarter_lte",
        "created_at_quarter_range",
        "created_at_quarter_starts_with",
        "created_at_range",
        "created_at_second",
        "created_at_second_contains",
        "created_at_second_ends_with",
        "created_at_second_gt",
        "created_at_second_gte",
        "created_at_second_in",
        "created_at_second_lt",
        "created_at_second_lte",
        "created_at_second_range",
        "created_at_second_starts_with",
        "created_at_time",
        "created_at_time_contains",
        "created_at_time_ends_with",
        "created_at_time_gt",
        "created_at_time_gte",
        "created_at_time_in",
        "created_at_time_lt",
        "created_at_time_lte",
        "created_at_time_range",
        "created_at_time_starts_with",
        "created_at_week",
        "created_at_week_contains",
        "created_at_week_day",
        "created_at_week_day_contains",
        "created_at_week_day_ends_with",
        "created_at_week_day_gt",
        "created_at_week_day_gte",
        "created_at_week_day_in",
        "created_at_week_day_lt",
        "created_at_week_day_lte",
        "created_at_week_day_range",
        "created_at_week_day_starts_with",
        "created_at_week_ends_with",
        "created_at_week_gt",
        "created_at_week_gte",
        "created_at_week_in",
        "created_at_week_lt",
        "created_at_week_lte",
        "created_at_week_range",
        "created_at_week_starts_with",
        "created_at_year",
        "created_at_year_contains",
        "created_at_year_ends_with",
        "created_at_year_gt",
        "created_at_year_gte",
        "created_at_year_in",
        "created_at_year_lt",
        "created_at_year_lte",
        "created_at_year_range",
        "created_at_year_starts_with",
    ]


def test_get_filters_for_model__boolean_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    done_field_names = sorted(name for name in fields if name.startswith("done"))
    assert done_field_names == ["done"]


def test_get_filters_for_model__date_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    due_by_field_names = sorted(name for name in fields if name.startswith("due_by"))
    assert due_by_field_names == [
        "due_by",
        "due_by_day",
        "due_by_day_contains",
        "due_by_day_ends_with",
        "due_by_day_gt",
        "due_by_day_gte",
        "due_by_day_in",
        "due_by_day_lt",
        "due_by_day_lte",
        "due_by_day_range",
        "due_by_day_starts_with",
        "due_by_gt",
        "due_by_gte",
        "due_by_in",
        "due_by_is_null",
        "due_by_iso_week_day",
        "due_by_iso_week_day_contains",
        "due_by_iso_week_day_ends_with",
        "due_by_iso_week_day_gt",
        "due_by_iso_week_day_gte",
        "due_by_iso_week_day_in",
        "due_by_iso_week_day_lt",
        "due_by_iso_week_day_lte",
        "due_by_iso_week_day_range",
        "due_by_iso_week_day_starts_with",
        "due_by_iso_year",
        "due_by_iso_year_contains",
        "due_by_iso_year_ends_with",
        "due_by_iso_year_gt",
        "due_by_iso_year_gte",
        "due_by_iso_year_in",
        "due_by_iso_year_lt",
        "due_by_iso_year_lte",
        "due_by_iso_year_range",
        "due_by_iso_year_starts_with",
        "due_by_lt",
        "due_by_lte",
        "due_by_month",
        "due_by_month_contains",
        "due_by_month_ends_with",
        "due_by_month_gt",
        "due_by_month_gte",
        "due_by_month_in",
        "due_by_month_lt",
        "due_by_month_lte",
        "due_by_month_range",
        "due_by_month_starts_with",
        "due_by_quarter",
        "due_by_quarter_contains",
        "due_by_quarter_ends_with",
        "due_by_quarter_gt",
        "due_by_quarter_gte",
        "due_by_quarter_in",
        "due_by_quarter_lt",
        "due_by_quarter_lte",
        "due_by_quarter_range",
        "due_by_quarter_starts_with",
        "due_by_range",
        "due_by_week",
        "due_by_week_contains",
        "due_by_week_day",
        "due_by_week_day_contains",
        "due_by_week_day_ends_with",
        "due_by_week_day_gt",
        "due_by_week_day_gte",
        "due_by_week_day_in",
        "due_by_week_day_lt",
        "due_by_week_day_lte",
        "due_by_week_day_range",
        "due_by_week_day_starts_with",
        "due_by_week_ends_with",
        "due_by_week_gt",
        "due_by_week_gte",
        "due_by_week_in",
        "due_by_week_lt",
        "due_by_week_lte",
        "due_by_week_range",
        "due_by_week_starts_with",
        "due_by_year",
        "due_by_year_contains",
        "due_by_year_ends_with",
        "due_by_year_gt",
        "due_by_year_gte",
        "due_by_year_in",
        "due_by_year_lt",
        "due_by_year_lte",
        "due_by_year_range",
        "due_by_year_starts_with",
    ]


def test_get_filters_for_model__time_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    check_time_field_names = sorted(name for name in fields if name.startswith("check_time"))
    assert check_time_field_names == [
        "check_time",
        "check_time_contains",
        "check_time_ends_with",
        "check_time_gt",
        "check_time_gte",
        "check_time_hour",
        "check_time_hour_contains",
        "check_time_hour_ends_with",
        "check_time_hour_gt",
        "check_time_hour_gte",
        "check_time_hour_in",
        "check_time_hour_lt",
        "check_time_hour_lte",
        "check_time_hour_range",
        "check_time_hour_starts_with",
        "check_time_in",
        "check_time_is_null",
        "check_time_lt",
        "check_time_lte",
        "check_time_minute",
        "check_time_minute_contains",
        "check_time_minute_ends_with",
        "check_time_minute_gt",
        "check_time_minute_gte",
        "check_time_minute_in",
        "check_time_minute_lt",
        "check_time_minute_lte",
        "check_time_minute_range",
        "check_time_minute_starts_with",
        "check_time_range",
        "check_time_second",
        "check_time_second_contains",
        "check_time_second_ends_with",
        "check_time_second_gt",
        "check_time_second_gte",
        "check_time_second_in",
        "check_time_second_lt",
        "check_time_second_lte",
        "check_time_second_range",
        "check_time_second_starts_with",
        "check_time_starts_with",
    ]


def test_get_filters_for_model__integer_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    points_field_names = sorted(name for name in fields if name.startswith("points"))
    assert points_field_names == [
        "points",
        "points_contains",
        "points_ends_with",
        "points_gt",
        "points_gte",
        "points_in",
        "points_is_null",
        "points_lt",
        "points_lte",
        "points_range",
        "points_starts_with",
    ]


def test_get_filters_for_model__decimal_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    progress_field_names = sorted(name for name in fields if name.startswith("progress"))
    assert progress_field_names == [
        "progress",
        "progress_contains",
        "progress_ends_with",
        "progress_gt",
        "progress_gte",
        "progress_in",
        "progress_lt",
        "progress_lte",
        "progress_range",
        "progress_starts_with",
    ]


def test_get_filters_for_model__duration_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    worked_hours_field_names = sorted(name for name in fields if name.startswith("worked_hours"))
    assert worked_hours_field_names == [
        "worked_hours",
        "worked_hours_gt",
        "worked_hours_gte",
        "worked_hours_in",
        "worked_hours_lt",
        "worked_hours_lte",
        "worked_hours_range",
    ]


def test_get_filters_for_model__email_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    contact_email_field_names = sorted(name for name in fields if name.startswith("contact_email"))
    assert contact_email_field_names == [
        "contact_email",
        "contact_email_contains",
        "contact_email_contains_exact",
        "contact_email_ends_with",
        "contact_email_ends_with_exact",
        "contact_email_exact",
        "contact_email_in",
        "contact_email_is_null",
        "contact_email_starts_with",
        "contact_email_starts_with_exact",
    ]


def test_get_filters_for_model__url_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    demo_url_field_names = sorted(name for name in fields if name.startswith("demo_url"))
    assert demo_url_field_names == [
        "demo_url",
        "demo_url_contains",
        "demo_url_contains_exact",
        "demo_url_ends_with",
        "demo_url_ends_with_exact",
        "demo_url_exact",
        "demo_url_in",
        "demo_url_is_null",
        "demo_url_starts_with",
        "demo_url_starts_with_exact",
    ]


def test_get_filters_for_model__uuid_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    external_uuid_field_names = sorted(name for name in fields if name.startswith("external_uuid"))
    assert external_uuid_field_names == [
        "external_uuid",
        "external_uuid_contains",
        "external_uuid_ends_with",
        "external_uuid_in",
        "external_uuid_is_null",
        "external_uuid_starts_with",
    ]


def test_get_filters_for_model__json_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    extra_data_field_names = sorted(name for name in fields if name.startswith("extra_data"))
    assert extra_data_field_names == [
        "extra_data",
        "extra_data_contained_by",
        "extra_data_contains",
        "extra_data_has_any_keys",
        "extra_data_has_key",
        "extra_data_has_keys",
        "extra_data_in",
        "extra_data_is_null",
    ]


def test_get_filters_for_model__image_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    image_field_names = sorted(name for name in fields if name.startswith("image"))
    assert image_field_names == [
        "image",
        "image_contains",
        "image_ends_with",
        "image_in",
        "image_is_null",
        "image_starts_with",
    ]


def test_get_filters_for_model__file_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    attachment_field_names = sorted(name for name in fields if name.startswith("attachment"))
    assert attachment_field_names == [
        "attachment",
        "attachment_contains",
        "attachment_ends_with",
        "attachment_in",
        "attachment_is_null",
        "attachment_starts_with",
    ]


def test_get_filters_for_model__one_related_field() -> None:
    fields = get_filters_for_model(Example, exclude=[])

    fk_field_names = sorted(name for name in fields if name.startswith("one_relation"))
    assert fk_field_names == [
        "one_relation",
        "one_relation_gt",
        "one_relation_gte",
        "one_relation_in",
        "one_relation_lt",
        "one_relation_lte",
    ]


def test_get_filters_for_model__many_related_field() -> None:
    fields = get_filters_for_model(Task, exclude=[])

    fk_field_names = sorted(name for name in fields if name.startswith("assignees"))
    assert fk_field_names == [
        "assignees",
        "assignees_gt",
        "assignees_gte",
        "assignees_in",
        "assignees_lt",
        "assignees_lte",
    ]


def test_get_filters_for_model__many_related_field__reverse() -> None:
    fields = get_filters_for_model(Task, exclude=[])

    fk_field_names = sorted(name for name in fields if name.startswith("reports"))
    assert fk_field_names == [
        "reports",
        "reports_gt",
        "reports_gte",
        "reports_in",
        "reports_lt",
        "reports_lte",
    ]


def test_get_filters_for_model__distinct() -> None:
    filters = get_filters_for_model(Task, exclude=[])

    frt = filters["project"]
    assert frt.distinct is False

    frt = filters["assignees"]
    assert frt.distinct is True
