from django.contrib.postgres.fields import ArrayField, HStoreField, RangeField
from django.contrib.postgres.fields.ranges import (
    BigIntegerRangeField,
    ContinuousRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    IntegerRangeField,
)
from django.db.models import (
    AutoField,
    BigAutoField,
    BigIntegerField,
    BinaryField,
    BooleanField,
    CharField,
    CommaSeparatedIntegerField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    EmailField,
    FileField,
    FilePathField,
    FloatField,
    GenericIPAddressField,
    ImageField,
    IntegerField,
    IPAddressField,
    JSONField,
    NullBooleanField,
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

from undine.converters import convert_to_filter_lookups


def test_convert_to_filter_lookups__booleanfield():
    lookups = convert_to_filter_lookups(BooleanField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__charfield():
    lookups = convert_to_filter_lookups(CharField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__commaseparatedintegerfield():
    lookups = convert_to_filter_lookups(CommaSeparatedIntegerField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__datefield():
    lookups = convert_to_filter_lookups(DateField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "day",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "iso_week_day",
        "iso_year",
        "istartswith",
        "lt",
        "lte",
        "month",
        "quarter",
        "range",
        "regex",
        "startswith",
        "week",
        "week_day",
        "year",
    ]


def test_convert_to_filter_lookups__datetimefield():
    lookups = convert_to_filter_lookups(DateTimeField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "date",
        "day",
        "endswith",
        "exact",
        "gt",
        "gte",
        "hour",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "iso_week_day",
        "iso_year",
        "istartswith",
        "lt",
        "lte",
        "minute",
        "month",
        "quarter",
        "range",
        "regex",
        "second",
        "startswith",
        "time",
        "week",
        "week_day",
        "year",
    ]


def test_convert_to_filter_lookups__decimalfield():
    lookups = convert_to_filter_lookups(DecimalField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__durationfield():
    lookups = convert_to_filter_lookups(DurationField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__emailfield():
    lookups = convert_to_filter_lookups(EmailField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__file_path_field():
    lookups = convert_to_filter_lookups(FilePathField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__floatfield():
    lookups = convert_to_filter_lookups(FloatField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__integerfield():
    lookups = convert_to_filter_lookups(IntegerField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__bigintegerfield():
    lookups = convert_to_filter_lookups(BigIntegerField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__smallintegerfield():
    lookups = convert_to_filter_lookups(SmallIntegerField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__ipaddressfield():
    lookups = convert_to_filter_lookups(IPAddressField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__genericipaddressfield():
    lookups = convert_to_filter_lookups(GenericIPAddressField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__nullbooleanfield():
    lookups = convert_to_filter_lookups(NullBooleanField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__positivebigintegerfield():
    lookups = convert_to_filter_lookups(PositiveBigIntegerField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__positiveintegerfield():
    lookups = convert_to_filter_lookups(PositiveIntegerField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__positivesmallintegerfield():
    lookups = convert_to_filter_lookups(PositiveSmallIntegerField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__slugfield():
    lookups = convert_to_filter_lookups(SlugField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__textfield():
    lookups = convert_to_filter_lookups(TextField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__timefield():
    lookups = convert_to_filter_lookups(TimeField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "hour",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "minute",
        "range",
        "regex",
        "second",
        "startswith",
    ]


def test_convert_to_filter_lookups__urlfield():
    lookups = convert_to_filter_lookups(URLField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__binaryfield():
    lookups = convert_to_filter_lookups(BinaryField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__uuidfield():
    lookups = convert_to_filter_lookups(UUIDField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__autofield():
    lookups = convert_to_filter_lookups(AutoField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__bigautofield():
    lookups = convert_to_filter_lookups(BigAutoField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__smallautofield():
    lookups = convert_to_filter_lookups(SmallAutoField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__jsonfield():
    lookups = convert_to_filter_lookups(JSONField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "has_any_keys",
        "has_key",
        "has_keys",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__filefield():
    lookups = convert_to_filter_lookups(FileField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__imagefield():
    lookups = convert_to_filter_lookups(ImageField())

    assert sorted(lookups) == [
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__arrayfield():
    lookups = convert_to_filter_lookups(ArrayField(CharField()))

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "len",
        "lt",
        "lte",
        "overlap",
        "range",
        "regex",
        "startswith",
    ]


def test_convert_to_filter_lookups__hstorefield():
    lookups = convert_to_filter_lookups(HStoreField())

    assert sorted(lookups) == [
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "gt",
        "gte",
        "has_any_keys",
        "has_key",
        "has_keys",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isnull",
        "istartswith",
        "keys",
        "lt",
        "lte",
        "range",
        "regex",
        "startswith",
        "values",
    ]


def test_convert_to_filter_lookups__rangefield():
    lookups = convert_to_filter_lookups(RangeField())

    assert sorted(lookups) == [
        "adjacent_to",
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "fully_gt",
        "fully_lt",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isempty",
        "isnull",
        "istartswith",
        "lower_inc",
        "lower_inf",
        "lt",
        "lte",
        "not_gt",
        "not_lt",
        "overlap",
        "range",
        "regex",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]


def test_convert_to_filter_lookups__continuousrangefield():
    lookups = convert_to_filter_lookups(ContinuousRangeField())

    assert sorted(lookups) == [
        "adjacent_to",
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "fully_gt",
        "fully_lt",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isempty",
        "isnull",
        "istartswith",
        "lower_inc",
        "lower_inf",
        "lt",
        "lte",
        "not_gt",
        "not_lt",
        "overlap",
        "range",
        "regex",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]


def test_convert_to_filter_lookups__integerrangefield():
    lookups = convert_to_filter_lookups(IntegerRangeField())

    assert sorted(lookups) == [
        "adjacent_to",
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "fully_gt",
        "fully_lt",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isempty",
        "isnull",
        "istartswith",
        "lower_inc",
        "lower_inf",
        "lt",
        "lte",
        "not_gt",
        "not_lt",
        "overlap",
        "range",
        "regex",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]


def test_convert_to_filter_lookups__bigintegerrangefield():
    lookups = convert_to_filter_lookups(BigIntegerRangeField())

    assert sorted(lookups) == [
        "adjacent_to",
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "fully_gt",
        "fully_lt",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isempty",
        "isnull",
        "istartswith",
        "lower_inc",
        "lower_inf",
        "lt",
        "lte",
        "not_gt",
        "not_lt",
        "overlap",
        "range",
        "regex",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]


def test_convert_to_filter_lookups__decimalrangefield():
    lookups = convert_to_filter_lookups(DecimalRangeField())

    assert sorted(lookups) == [
        "adjacent_to",
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "fully_gt",
        "fully_lt",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isempty",
        "isnull",
        "istartswith",
        "lower_inc",
        "lower_inf",
        "lt",
        "lte",
        "not_gt",
        "not_lt",
        "overlap",
        "range",
        "regex",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]


def test_convert_to_filter_lookups__datetimerangefield():
    lookups = convert_to_filter_lookups(DateTimeRangeField())

    assert sorted(lookups) == [
        "adjacent_to",
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "fully_gt",
        "fully_lt",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isempty",
        "isnull",
        "istartswith",
        "lower_inc",
        "lower_inf",
        "lt",
        "lte",
        "not_gt",
        "not_lt",
        "overlap",
        "range",
        "regex",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]


def test_convert_to_filter_lookups__daterangefield():
    lookups = convert_to_filter_lookups(DateRangeField())

    assert sorted(lookups) == [
        "adjacent_to",
        "contained_by",
        "contains",
        "endswith",
        "exact",
        "fully_gt",
        "fully_lt",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "iregex",
        "isempty",
        "isnull",
        "istartswith",
        "lower_inc",
        "lower_inf",
        "lt",
        "lte",
        "not_gt",
        "not_lt",
        "overlap",
        "range",
        "regex",
        "startswith",
        "upper_inc",
        "upper_inf",
    ]
