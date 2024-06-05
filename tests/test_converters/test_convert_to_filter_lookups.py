from __future__ import annotations

import pytest
from django.db.models import (
    CASCADE,
    AutoField,
    BigAutoField,
    BigIntegerField,
    BinaryField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    EmailField,
    FileField,
    FilePathField,
    FloatField,
    ForeignKey,
    GenericIPAddressField,
    ImageField,
    IntegerField,
    IPAddressField,
    JSONField,
    ManyToOneRel,
    NullBooleanField,
    OneToOneField,
    OneToOneRel,
    PositiveBigIntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    SlugField,
    SmallAutoField,
    SmallIntegerField,
    TextField,
    TimeField,
    URLField,
    UUIDField,
)

from example_project.app.models import Comment, Task
from undine.converters import convert_to_filter_lookups

try:
    from django.db.backends.postgresql import psycopg_any
except ImportError:
    psycopg_any = None


def test_convert_to_filter_lookups__boolean_field() -> None:
    lookups = convert_to_filter_lookups(BooleanField())

    expected = [
        "exact",
    ]

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__char_field(null) -> None:
    lookups = convert_to_filter_lookups(CharField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "istartswith",
        "startswith",
    ]

    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__date_field(null) -> None:
    lookups = convert_to_filter_lookups(DateField(null=null))

    expected = [
        "day",
        "day__contains",
        "day__endswith",
        "day__gt",
        "day__gte",
        "day__in",
        "day__lt",
        "day__lte",
        "day__range",
        "day__startswith",
        "exact",
        "gt",
        "gte",
        "in",
        "iso_week_day",
        "iso_week_day__contains",
        "iso_week_day__endswith",
        "iso_week_day__gt",
        "iso_week_day__gte",
        "iso_week_day__in",
        "iso_week_day__lt",
        "iso_week_day__lte",
        "iso_week_day__range",
        "iso_week_day__startswith",
        "iso_year",
        "iso_year__contains",
        "iso_year__endswith",
        "iso_year__gt",
        "iso_year__gte",
        "iso_year__in",
        "iso_year__lt",
        "iso_year__lte",
        "iso_year__range",
        "iso_year__startswith",
        "lt",
        "lte",
        "month",
        "month__contains",
        "month__endswith",
        "month__gt",
        "month__gte",
        "month__in",
        "month__lt",
        "month__lte",
        "month__range",
        "month__startswith",
        "quarter",
        "quarter__contains",
        "quarter__endswith",
        "quarter__gt",
        "quarter__gte",
        "quarter__in",
        "quarter__lt",
        "quarter__lte",
        "quarter__range",
        "quarter__startswith",
        "range",
        "week",
        "week__contains",
        "week__endswith",
        "week__gt",
        "week__gte",
        "week__in",
        "week__lt",
        "week__lte",
        "week__range",
        "week__startswith",
        "week_day",
        "week_day__contains",
        "week_day__endswith",
        "week_day__gt",
        "week_day__gte",
        "week_day__in",
        "week_day__lt",
        "week_day__lte",
        "week_day__range",
        "week_day__startswith",
        "year",
        "year__contains",
        "year__endswith",
        "year__gt",
        "year__gte",
        "year__in",
        "year__lt",
        "year__lte",
        "year__range",
        "year__startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__datetime_field(null) -> None:
    lookups = convert_to_filter_lookups(DateTimeField(null=null))

    expected = [
        "date",
        "date__gt",
        "date__gte",
        "date__in",
        "date__lt",
        "date__lte",
        "date__range",
        "day",
        "day__contains",
        "day__endswith",
        "day__gt",
        "day__gte",
        "day__in",
        "day__lt",
        "day__lte",
        "day__range",
        "day__startswith",
        "exact",
        "gt",
        "gte",
        "hour",
        "hour__contains",
        "hour__endswith",
        "hour__gt",
        "hour__gte",
        "hour__in",
        "hour__lt",
        "hour__lte",
        "hour__range",
        "hour__startswith",
        "in",
        "iso_week_day",
        "iso_week_day__contains",
        "iso_week_day__endswith",
        "iso_week_day__gt",
        "iso_week_day__gte",
        "iso_week_day__in",
        "iso_week_day__lt",
        "iso_week_day__lte",
        "iso_week_day__range",
        "iso_week_day__startswith",
        "iso_year",
        "iso_year__contains",
        "iso_year__endswith",
        "iso_year__gt",
        "iso_year__gte",
        "iso_year__in",
        "iso_year__lt",
        "iso_year__lte",
        "iso_year__range",
        "iso_year__startswith",
        "lt",
        "lte",
        "minute",
        "minute__contains",
        "minute__endswith",
        "minute__gt",
        "minute__gte",
        "minute__in",
        "minute__lt",
        "minute__lte",
        "minute__range",
        "minute__startswith",
        "month",
        "month__contains",
        "month__endswith",
        "month__gt",
        "month__gte",
        "month__in",
        "month__lt",
        "month__lte",
        "month__range",
        "month__startswith",
        "quarter",
        "quarter__contains",
        "quarter__endswith",
        "quarter__gt",
        "quarter__gte",
        "quarter__in",
        "quarter__lt",
        "quarter__lte",
        "quarter__range",
        "quarter__startswith",
        "range",
        "second",
        "second__contains",
        "second__endswith",
        "second__gt",
        "second__gte",
        "second__in",
        "second__lt",
        "second__lte",
        "second__range",
        "second__startswith",
        "time",
        "time__contains",
        "time__endswith",
        "time__gt",
        "time__gte",
        "time__in",
        "time__lt",
        "time__lte",
        "time__range",
        "time__startswith",
        "week",
        "week__contains",
        "week__endswith",
        "week__gt",
        "week__gte",
        "week__in",
        "week__lt",
        "week__lte",
        "week__range",
        "week__startswith",
        "week_day",
        "week_day__contains",
        "week_day__endswith",
        "week_day__gt",
        "week_day__gte",
        "week_day__in",
        "week_day__lt",
        "week_day__lte",
        "week_day__range",
        "week_day__startswith",
        "year",
        "year__contains",
        "year__endswith",
        "year__gt",
        "year__gte",
        "year__in",
        "year__lt",
        "year__lte",
        "year__range",
        "year__startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__decimal_field(null) -> None:
    lookups = convert_to_filter_lookups(DecimalField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__duration_field(null) -> None:
    lookups = convert_to_filter_lookups(DurationField(null=null))

    expected = [
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__email_field(null) -> None:
    lookups = convert_to_filter_lookups(EmailField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "istartswith",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__file_path__field(null) -> None:
    lookups = convert_to_filter_lookups(FilePathField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "istartswith",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__float_field(null) -> None:
    lookups = convert_to_filter_lookups(FloatField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__integer_field(null) -> None:
    lookups = convert_to_filter_lookups(IntegerField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__big_integer_field(null) -> None:
    lookups = convert_to_filter_lookups(BigIntegerField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__small_integer_field(null) -> None:
    lookups = convert_to_filter_lookups(SmallIntegerField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__ipaddress_field(null) -> None:
    lookups = convert_to_filter_lookups(IPAddressField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "istartswith",
        "startswith",
    ]


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__generic_ipaddress_field(null) -> None:
    lookups = convert_to_filter_lookups(GenericIPAddressField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "istartswith",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


def test_convert_to_filter_lookups__null_boolean_field() -> None:
    lookups = convert_to_filter_lookups(NullBooleanField())

    expected = [
        "exact",
        "in",
        "isnull",
    ]

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__positive_big_integer_field(null) -> None:
    lookups = convert_to_filter_lookups(PositiveBigIntegerField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__positiveinteger_field(null) -> None:
    lookups = convert_to_filter_lookups(PositiveIntegerField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__positive_small_integer_field(null) -> None:
    lookups = convert_to_filter_lookups(PositiveSmallIntegerField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__slug_field(null) -> None:
    lookups = convert_to_filter_lookups(SlugField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "istartswith",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__text_field(null) -> None:
    lookups = convert_to_filter_lookups(TextField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "istartswith",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__time_field(null) -> None:
    lookups = convert_to_filter_lookups(TimeField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "hour",
        "hour__contains",
        "hour__endswith",
        "hour__gt",
        "hour__gte",
        "hour__in",
        "hour__lt",
        "hour__lte",
        "hour__range",
        "hour__startswith",
        "in",
        "lt",
        "lte",
        "minute",
        "minute__contains",
        "minute__endswith",
        "minute__gt",
        "minute__gte",
        "minute__in",
        "minute__lt",
        "minute__lte",
        "minute__range",
        "minute__startswith",
        "range",
        "second",
        "second__contains",
        "second__endswith",
        "second__gt",
        "second__gte",
        "second__in",
        "second__lt",
        "second__lte",
        "second__range",
        "second__startswith",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__url_field(null) -> None:
    lookups = convert_to_filter_lookups(URLField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "istartswith",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__binary_field(null) -> None:
    lookups = convert_to_filter_lookups(BinaryField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "in",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__uuid_field(null) -> None:
    lookups = convert_to_filter_lookups(UUIDField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "in",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__auto_field(null) -> None:
    lookups = convert_to_filter_lookups(AutoField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__big_auto_field(null) -> None:
    lookups = convert_to_filter_lookups(BigAutoField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__small_auto_field(null) -> None:
    lookups = convert_to_filter_lookups(SmallAutoField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
        "range",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__json_field(null) -> None:
    lookups = convert_to_filter_lookups(JSONField(null=null))

    expected = [
        "contained_by",
        "contains",
        "exact",
        "has_any_keys",
        "has_key",
        "has_keys",
        "in",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__file_field(null) -> None:
    lookups = convert_to_filter_lookups(FileField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "in",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__image_field(null) -> None:
    lookups = convert_to_filter_lookups(ImageField(null=null))

    expected = [
        "contains",
        "endswith",
        "exact",
        "in",
        "startswith",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__one_to_one_field(null) -> None:
    field = OneToOneField(to="...", on_delete=CASCADE, null=null)
    lookups = convert_to_filter_lookups(field)

    expected = [
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__foreignkey(null) -> None:
    field = ForeignKey(to="...", on_delete=CASCADE, null=null)
    lookups = convert_to_filter_lookups(field)

    expected = [
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__reverse_one_to_one_field(null) -> None:
    field = OneToOneField(to="...", on_delete=CASCADE, null=null)
    rel = OneToOneRel(field, to="...", field_name="...")
    lookups = convert_to_filter_lookups(rel)

    expected = [
        "exact",
        "gt",
        "gte",
        "in",
        "isnull",  # reverse relation still nullable
        "lt",
        "lte",
    ]

    assert sorted(lookups) == sorted(expected)


@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__reverse_foreignkey(null) -> None:
    field = ForeignKey(to="...", on_delete=CASCADE, null=null)
    rel = ManyToOneRel(field, to="...", field_name="...")
    lookups = convert_to_filter_lookups(rel)

    expected = [
        "exact",
        "gt",
        "gte",
        "in",
        "isnull",  # reverse relation still nullable
        "lt",
        "lte",
    ]

    assert sorted(lookups) == sorted(expected)


def test_convert_to_filter_lookups__many_to_many() -> None:
    field = Task._meta.get_field("assignees")
    lookups = convert_to_filter_lookups(field)

    expected = [
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
    ]

    assert sorted(lookups) == sorted(expected)


def test_convert_to_filter_lookups__reverse_many_to_many() -> None:
    field = Task._meta.get_field("reports")
    lookups = convert_to_filter_lookups(field)

    expected = [
        "exact",
        "gt",
        "gte",
        "in",
        "lt",
        "lte",
    ]

    assert sorted(lookups) == sorted(expected)


def test_convert_to_filter_lookups__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")
    lookups = convert_to_filter_lookups(field)

    assert sorted(lookups) == []


def test_convert_to_filter_lookups__generic_relation() -> None:
    field = Task._meta.get_field("comments")
    lookups = convert_to_filter_lookups(field)

    expected = [
        "exact",
        "gt",
        "gte",
        "in",
        "isnull",
        "lt",
        "lte",
    ]
    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__array_field(null) -> None:
    from django.contrib.postgres.fields import ArrayField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(ArrayField(CharField(), null=null))

    expected = [
        "contained_by",
        "contains",
        "exact",
        "len",
        "len__contains",
        "len__endswith",
        "len__gt",
        "len__gte",
        "len__in",
        "len__lt",
        "len__lte",
        "len__range",
        "len__startswith",
        "overlap",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__hstore_field(null) -> None:
    from django.contrib.postgres.fields import HStoreField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(HStoreField(null=null))

    expected = [
        "contained_by",
        "contains",
        "exact",
        "has_any_keys",
        "has_key",
        "has_keys",
        "keys",
        "keys__contained_by",
        "keys__contains",
        "keys__len",
        "keys__len__contains",
        "keys__len__endswith",
        "keys__len__gt",
        "keys__len__gte",
        "keys__len__in",
        "keys__len__lt",
        "keys__len__lte",
        "keys__len__range",
        "keys__len__startswith",
        "keys__overlap",
        "values",
        "values__contained_by",
        "values__contains",
        "values__len",
        "values__len__contains",
        "values__len__endswith",
        "values__len__gt",
        "values__len__gte",
        "values__len__in",
        "values__len__lt",
        "values__len__lte",
        "values__len__range",
        "values__len__startswith",
        "values__overlap",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__range_field(null) -> None:
    from django.contrib.postgres.fields import RangeField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(RangeField(null=null))

    expected = [
        "endswith",
        "exact",
        "isempty",
        "lower_inc",
        "lower_inf",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__continuous_range_field(null) -> None:
    from django.contrib.postgres.fields.ranges import ContinuousRangeField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(ContinuousRangeField(null=null))

    expected = [
        "endswith",
        "exact",
        "isempty",
        "lower_inc",
        "lower_inf",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__integer_range_field(null) -> None:
    from django.contrib.postgres.fields import IntegerRangeField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(IntegerRangeField(null=null))

    expected = [
        "endswith",
        "exact",
        "isempty",
        "lower_inc",
        "lower_inf",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__big_integer_range_field(null) -> None:
    from django.contrib.postgres.fields import BigIntegerRangeField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(BigIntegerRangeField(null=null))

    expected = [
        "endswith",
        "exact",
        "isempty",
        "lower_inc",
        "lower_inf",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__decimal_range_field(null) -> None:
    from django.contrib.postgres.fields import DecimalRangeField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(DecimalRangeField(null=null))

    expected = [
        "endswith",
        "exact",
        "isempty",
        "lower_inc",
        "lower_inf",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__datetimerange_field(null) -> None:
    from django.contrib.postgres.fields import DateTimeRangeField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(DateTimeRangeField(null=null))

    expected = [
        "endswith",
        "exact",
        "isempty",
        "lower_inc",
        "lower_inf",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)


@pytest.mark.skipif(psycopg_any is None, reason="psycopg is not installed")
@pytest.mark.parametrize("null", [True, False])
def test_convert_to_filter_lookups__daterange_field(null) -> None:
    from django.contrib.postgres.fields import DateRangeField  # noqa: PLC0415

    lookups = convert_to_filter_lookups(DateRangeField(null=null))

    expected = [
        "endswith",
        "exact",
        "isempty",
        "lower_inc",
        "lower_inf",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]
    if null:
        expected.append("isnull")

    assert sorted(lookups) == sorted(expected)
