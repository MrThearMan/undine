from __future__ import annotations

import binascii
import dataclasses
import itertools
import json
from copy import copy
from typing import TYPE_CHECKING, Any, Literal

from django.core.exceptions import FieldDoesNotExist
from django.db import router  # noqa: ICN003
from django.db.models import F, Q, Value
from django.db.models.constants import LOOKUP_SEP

from undine.exceptions import GraphQLPaginationArgumentValidationError
from undine.settings import undine_settings
from undine.utils.model_utils import determine_output_field, get_db_features, get_model_field

from .utils import decode_base64, encode_base64

if TYPE_CHECKING:
    from django.db.models import Field as DjangoField
    from django.db.models import Model, OrderBy


__all__ = [
    "OrderingDescriptor",
    "build_keyset_filter",
    "decode_cursor",
    "decode_cursor_payload",
    "encode_cursor",
    "order_by_list_to_ordering_descriptors",
    "parse_cursor_values",
]


@dataclasses.dataclass(frozen=True, slots=True)
class OrderingDescriptor:
    """Describes a single value the paginated queryset is ordered by."""

    attname: str
    """The name the ordering value can be read from on a fetched row, and filtered by on the queryset."""

    order_by: OrderBy
    """The resolved `ORDER BY` expression this describes."""

    output_field: DjangoField
    """The model field the ordering value is serialized and deserialized with."""

    maybe_null: bool = True
    """Whether the ordering value can be `None`. Assume it can unless known otherwise."""

    nulls_first: bool = False
    """Whether null values are ordered before non-null values."""

    is_primary_key: bool = False
    """Whether the ordering value is the primary key on the model it will be applied to."""

    def get_comparison(self, value: Value | None, *, before: bool) -> Q | None:
        """Build a condition matching all rows ordered before/after the given value."""
        if value is None:
            # Nothing is ordered before the first null value, or after the last null value,
            # so those cases need no condition at all. In the other direction, every
            # non-null value is on the correct side of the null value.
            if self.nulls_first ^ before:
                return Q((f"{self.attname}{LOOKUP_SEP}isnull", False))
            return None

        lookup = "lt" if self.order_by.descending ^ before else "gt"
        comparison = Q((f"{self.attname}{LOOKUP_SEP}{lookup}", value))

        # Null values are never matched by a `lt`/`gt` comparison, so they have to be added explicitly.
        if self.maybe_null and self.nulls_first == before:
            comparison |= Q((f"{self.attname}{LOOKUP_SEP}isnull", True))

        return comparison

    def get_equality(self, value: Value | None) -> Q:
        """Build a condition matching all rows with the given ordering value."""
        if value is None:
            return Q((f"{self.attname}{LOOKUP_SEP}isnull", True))
        return Q((f"{self.attname}{LOOKUP_SEP}exact", value))

    def get_string_value(self, instance: Model) -> str | None:
        """Serialize this ordering value of the given instance so that it can be placed in a cursor."""
        value = getattr(instance, self.attname, None)
        if value is None:
            return None

        # Copy the output field and set the instance's attname to it in case the ordering value
        # is not available under the output field's original attname on the instance.
        # The output field might also no have attname set.
        output_field = copy(self.output_field)
        output_field.attname = self.attname
        return output_field.value_to_string(instance)


def encode_cursor(
    instance: Model,
    *,
    typename: str,
    descriptors: list[OrderingDescriptor],
) -> str:
    values = {descriptor.attname: descriptor.get_string_value(instance) for descriptor in descriptors}
    payload = json.dumps(values, separators=(",", ":"))
    return encode_base64(f"connection:{typename}:{payload}")


def decode_cursor(
    cursor: str,
    *,
    typename: str,
    descriptors: list[OrderingDescriptor],
    kind: Literal["before", "after"],
) -> Q:
    string_values = decode_cursor_payload(cursor, typename=typename, kind=kind)
    values = parse_cursor_values(string_values, descriptors=descriptors, typename=typename, kind=kind)
    return build_keyset_filter(descriptors, values, before=kind == "before")


def decode_cursor_payload(
    cursor: str,
    *,
    typename: str,
    kind: Literal["before", "after"],
) -> dict[str, str | None]:
    """Decode the given cursor into the raw string values it holds, keyed by attname."""
    try:
        decoded = decode_base64(cursor)
    except binascii.Error as error:
        msg = f"Argument '{kind}' is invalid: Not a valid cursor for type '{typename}'."
        raise GraphQLPaginationArgumentValidationError(msg) from error

    prefix = f"connection:{typename}:"

    if not decoded.startswith(prefix):
        msg = f"Argument '{kind}' is invalid: Not a valid cursor for type '{typename}'."
        raise GraphQLPaginationArgumentValidationError(msg)

    payload = decoded.removeprefix(prefix)

    string_values = json.loads(payload)
    is_valid = isinstance(string_values, dict) and all(
        isinstance(key, str) and (value is None or isinstance(value, str)) for key, value in string_values.items()
    )
    if not is_valid:
        msg = f"Argument '{kind}' is invalid: Not a valid cursor for type '{typename}'."
        raise GraphQLPaginationArgumentValidationError(msg)

    return string_values


def parse_cursor_values(
    string_values: dict[str, str | None],
    *,
    descriptors: list[OrderingDescriptor],
    typename: str,
    kind: Literal["before", "after"],
) -> dict[str, Value | None]:
    """Parse the raw string values of a cursor into values comparable against the given ordering."""
    if set(string_values) != {descriptor.attname for descriptor in descriptors}:
        msg = f"Argument '{kind}' is invalid: Cursor was created for a different ordering."
        raise GraphQLPaginationArgumentValidationError(msg)

    values: dict[str, Value | None] = {}

    for descriptor in descriptors:
        string_value = string_values[descriptor.attname]
        if string_value is None:
            values[descriptor.attname] = None
            continue

        try:
            value = descriptor.output_field.to_python(string_value)
        except Exception as error:
            msg = f"Argument '{kind}' is invalid: Not a valid cursor for type '{typename}'."
            raise GraphQLPaginationArgumentValidationError(msg) from error

        values[descriptor.attname] = Value(value, output_field=descriptor.output_field)

    return values


def build_keyset_filter(
    descriptors: list[OrderingDescriptor],
    values: dict[str, Value | None],
    *,
    before: bool,
) -> Q:
    """
    Build a condition matching all rows ordered before/after the row the given values were taken from.

    Since ordering can span multiple values, this is built as a nested comparison, where each
    level only applies if all the previous ordering values were equal:
    `a > x OR (a = x AND (b > y OR (b = y AND ...)))`
    """
    condition: Q | None = None

    for descriptor in reversed(descriptors):
        value = values[descriptor.attname]
        comparison = descriptor.get_comparison(value, before=before)

        if condition is None:
            condition = comparison
            continue

        equality = descriptor.get_equality(value)
        condition = equality & condition if comparison is None else comparison | (equality & condition)

    return condition if condition is not None else Q()


def order_by_list_to_ordering_descriptors(
    order_by_list: list[OrderBy],
    *,
    model: type[Model],
    annotations: dict[str, Any],
    only_fields: set[str],
) -> list[OrderingDescriptor]:
    descriptors: list[OrderingDescriptor] = []
    counter = itertools.count()

    for order_by in order_by_list:
        descriptor = _build_ordering_descriptor(
            order_by,
            model=model,
            counter=counter,
            annotations=annotations,
            only_fields=only_fields,
        )
        descriptors.append(descriptor)

    return descriptors


def _build_ordering_descriptor(
    order_by: OrderBy,
    *,
    model: type[Model],
    counter: itertools.count,
    annotations: dict[str, Any],
    only_fields: set[str],
) -> OrderingDescriptor:
    db_alias = router.db_for_read(model)
    nulls_first_by_default = get_db_features(db_alias).order_by_nulls_first != order_by.descending
    nulls_first = False if order_by.nulls_last else order_by.nulls_first or nulls_first_by_default

    expression = order_by.expression

    # Expressions and subqueries
    if not isinstance(expression, F):
        key = f"{undine_settings.PAGINATION_ORDERING_KEY}_{next(counter)}"
        field: DjangoField = copy(determine_output_field(expression, model=model))

        annotations[key] = expression
        return OrderingDescriptor(
            attname=key,
            order_by=order_by,
            output_field=field,
            maybe_null=field.null,
            nulls_first=nulls_first,
        )

    if expression.name == "pk":
        only_fields.add("pk")
        # Expression could be descending so don't use the OrderingDescriptor.for_pk() shortcut
        return OrderingDescriptor(
            attname=expression.name,
            order_by=order_by,
            output_field=model._meta.pk,  # type: ignore[arg-type]
            maybe_null=False,
            is_primary_key=True,
        )

    try:
        model_field: DjangoField = model._meta.get_field(expression.name)  # type: ignore[assignment]

    except FieldDoesNotExist:
        related_model_field: DjangoField = get_model_field(model=model, lookup=expression.name)  # type: ignore[assignment]

        key = f"{undine_settings.PAGINATION_ORDERING_KEY}_{next(counter)}"
        annotations[key] = expression
        return OrderingDescriptor(
            attname=key,
            order_by=order_by,
            output_field=related_model_field,
            maybe_null=related_model_field.null,
            nulls_first=nulls_first,
        )

    # Fields from the model itself
    attname = model_field.get_attname()
    only_fields.add(attname)
    return OrderingDescriptor(
        attname=attname,
        order_by=order_by,
        output_field=model_field,
        maybe_null=model_field.null,
        nulls_first=nulls_first,
        is_primary_key=model_field.primary_key,
    )
