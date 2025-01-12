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

from undine.filtering import get_filters_for_model


class Relation(Model):
    name = CharField(max_length=255)

    class Meta:
        managed = False
        app_label = __name__

    def __str__(self) -> str:
        return self.name


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

    relation = ForeignKey(Relation, on_delete=CASCADE, related_name="examples")

    class Meta:
        managed = False
        app_label = __name__

    def __str__(self) -> str:
        return self.name


def test_get_filters_for_model():
    fields = get_filters_for_model(Example, exclude=[])

    field_names = sorted(fields)

    # Primary key (integer field)
    pk_field_names = [name for name in field_names if name.startswith("pk")]
    assert pk_field_names == [
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
    ]

    # Char fields
    name_field_names = [name for name in field_names if name.startswith("name")]
    assert name_field_names == [
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
    ]

    # Char fields with choices
    type_field_names = [name for name in field_names if name.startswith("type")]
    assert type_field_names == [
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
    ]

    # DateTime fields
    created_at_field_names = [name for name in field_names if name.startswith("created_at")]
    assert created_at_field_names == [
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
    ]

    # Boolean fields
    done_field_names = [name for name in field_names if name.startswith("done")]
    assert done_field_names == [
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
    ]

    # Date fields
    due_by_field_names = [name for name in field_names if name.startswith("due_by")]
    assert due_by_field_names == [
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
    ]

    # Time fields
    check_time_field_names = [name for name in field_names if name.startswith("check_time")]
    assert check_time_field_names == [
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
    ]

    # Integer fields
    points_field_names = [name for name in field_names if name.startswith("points")]
    assert points_field_names == [
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
    ]

    # Decimal fields
    progress_field_names = [name for name in field_names if name.startswith("progress")]
    assert progress_field_names == [
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
    ]

    # Duration fields
    worked_hours_field_names = [name for name in field_names if name.startswith("worked_hours")]
    assert worked_hours_field_names == [
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

    # Email fields
    contact_email_field_names = [name for name in field_names if name.startswith("contact_email")]
    assert contact_email_field_names == [
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
    ]

    # URL fields
    demo_url_field_names = [name for name in field_names if name.startswith("demo_url")]
    assert demo_url_field_names == [
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
    ]

    # UUID fields
    external_uuid_field_names = [name for name in field_names if name.startswith("external_uuid")]
    assert external_uuid_field_names == [
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
    ]

    # JSON fields
    extra_data_field_names = [name for name in field_names if name.startswith("extra_data")]
    assert extra_data_field_names == [
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
    ]

    # Image fields
    image_field_names = [name for name in field_names if name.startswith("image")]
    assert image_field_names == [
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
    ]

    # File fields
    attachement_field_names = [name for name in field_names if name.startswith("attachment")]
    assert attachement_field_names == [
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
    ]


def test_get_filters_for_model__exclude():
    fields = get_filters_for_model(Example, exclude=["name", "created_at_gt"])

    field_names = sorted(fields)

    name_field_names = [name for name in field_names if name.startswith("name")]
    assert name_field_names == []

    created_at_field_names = [name for name in field_names if name.startswith("created_at")]
    assert "created_at_gt" not in created_at_field_names
