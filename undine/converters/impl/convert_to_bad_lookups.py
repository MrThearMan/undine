from __future__ import annotations

from contextlib import suppress
from typing import Any

from django.contrib.contenttypes.fields import GenericRelation
from django.db.models import (
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
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    NullBooleanField,
    OneToOneField,
    OneToOneRel,
    SlugField,
    TextField,
    TimeField,
    URLField,
    UUIDField,
)

from undine.converters.definitions import convert_to_bad_lookups
from undine.typing import SupportsLookup
from undine.utils.model_utils import get_many_to_many_through_field


@convert_to_bad_lookups.register
def _(_: SupportsLookup, **kwargs: Any) -> set[str]:
    return set()  # By default, don't exclude any lookups


@convert_to_bad_lookups.register
def _(_: BooleanField, **kwargs: Any) -> set[str]:
    return {
        "contains",
        "endswith",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "in",
        "isnull",
        "istartswith",
        "lt",
        "lte",
        "range",
        "startswith",
    }


@convert_to_bad_lookups.register
def _(
    field: (
        CharField
        | EmailField
        | FilePathField
        | IPAddressField
        | GenericIPAddressField
        | SlugField
        | TextField
        | URLField
    ),
    **kwargs: Any,
) -> set[str]:
    lookups = {
        "gt",
        "gte",
        "lt",
        "lte",
        "range",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: DateField, **kwargs: Any) -> set[str]:
    lookups = {
        "contained_by",
        "contains",
        "endswith",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
        "startswith",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: DateTimeField, **kwargs: Any) -> set[str]:
    lookups = {
        "contained_by",
        "contains",
        "endswith",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
        "startswith",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: DurationField, **kwargs: Any) -> set[str]:
    lookups = {
        "contains",
        "endswith",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
        "startswith",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: IntegerField | FloatField | DecimalField, **kwargs: Any) -> set[str]:
    lookups = {
        "contained_by",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(_: NullBooleanField, **kwargs: Any) -> set[str]:
    return {
        "contains",
        "endswith",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
        "lt",
        "lte",
        "range",
        "startswith",
    }


@convert_to_bad_lookups.register
def _(field: TimeField, **kwargs: Any) -> set[str]:
    lookups = {
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: BinaryField, **kwargs: Any) -> set[str]:
    lookups = {
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
        "lt",
        "lte",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: UUIDField, **kwargs: Any) -> set[str]:
    lookups = {
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
        "lt",
        "lte",
        "range",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: JSONField, **kwargs: Any) -> set[str]:
    lookups = {
        "endswith",
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
        "lt",
        "lte",
        "range",
        "startswith",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: FileField | ImageField, **kwargs: Any) -> set[str]:
    lookups: set[str] = {
        "gt",
        "gte",
        "icontains",
        "iendswith",
        "iexact",
        "istartswith",
        "lt",
        "lte",
        "range",
    }
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: OneToOneField | OneToOneRel | ForeignKey | ManyToOneRel, **kwargs: Any) -> set[str]:
    lookups: set[str] = set()
    if not field.null:
        lookups.add("isnull")
    return lookups


@convert_to_bad_lookups.register
def _(field: ManyToManyField | ManyToManyRel, **kwargs: Any) -> set[str]:
    through_field = get_many_to_many_through_field(field)

    # For many-to-many fields, any lookups are done to the corresponding field on the through-model.
    # Remove any lookups from the many-to-many fields' lookups that are not on the through-model field,
    # as well as any bad lookups registered for the the through-model field's type.
    bad_lookups = set(field.get_lookups()) - set(through_field.get_lookups())
    bad_lookups |= convert_to_bad_lookups(through_field)

    return bad_lookups


with suppress(ImportError):
    from django.contrib.postgres.fields import ArrayField, HStoreField, RangeField

    @convert_to_bad_lookups.register
    def _(field: ArrayField, **kwargs: Any) -> set[str]:
        lookups = {
            "endswith",
            "gt",
            "gte",
            "icontains",
            "iendswith",
            "iexact",
            "in",
            "istartswith",
            "lt",
            "lte",
            "range",
            "startswith",
        }
        if not field.null:
            lookups.add("isnull")
        return lookups

    @convert_to_bad_lookups.register
    def _(field: HStoreField, **kwargs: Any) -> set[str]:
        lookups = {
            "endswith",
            "gt",
            "gte",
            "icontains",
            "iendswith",
            "iexact",
            "in",
            "istartswith",
            "lt",
            "lte",
            "range",
            "startswith",
        }
        if not field.null:
            lookups.add("isnull")
        return lookups

    @convert_to_bad_lookups.register
    def _(field: RangeField, **kwargs: Any) -> set[str]:
        lookups = {
            "adjacent_to",
            "contained_by",
            "contains",
            "fully_gt",
            "fully_lt",
            "gt",
            "gte",
            "icontains",
            "iendswith",
            "iexact",
            "in",
            "istartswith",
            "lt",
            "lte",
            "not_gt",
            "not_lt",
            "overlap",
            "range",
        }
        if not field.null:
            lookups.add("isnull")
        return lookups


@convert_to_bad_lookups.register
def _(_: GenericRelation, **kwargs: Any) -> set[str]:
    return set()
