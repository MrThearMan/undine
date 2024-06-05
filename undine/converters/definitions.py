from __future__ import annotations

from copy import copy
from typing import Any

from django.db.models import Field, Lookup, Transform
from django.db.models.constants import LOOKUP_SEP
from django.db.models.functions import TruncDate, TruncTime
from graphql import GraphQLArgumentMap, GraphQLFieldResolver, GraphQLInputType, GraphQLOutputType, GraphQLType

from undine.typing import DjangoExpression, GraphQLFilterResolver, SupportsLookup
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.reflection import has_callable_attribute, is_subclass

__all__ = [
    "convert_lookup_to_graphql_type",
    "convert_to_bad_lookups",
    "convert_to_default_value",
    "convert_to_description",
    "convert_to_entrypoint_resolver",
    "convert_to_field_ref",
    "convert_to_field_resolver",
    "convert_to_filter_lookups",
    "convert_to_filter_ref",
    "convert_to_filter_resolver",
    "convert_to_graphql_argument_map",
    "convert_to_graphql_type",
    "convert_to_input_ref",
    "convert_to_order_ref",
    "convert_to_python_type",
    "extend_expression",
    "is_field_nullable",
    "is_input_hidden",
    "is_input_only",
    "is_input_required",
    "is_many",
]

# Converters are defined here without their implementations to avoid circular imports.
# The implementations are defined in the `impl` subpackage.
# These are then registered in `apps.py` when Django apps are ready.


convert_lookup_to_graphql_type: FunctionDispatcher[GraphQLType] = FunctionDispatcher()
"""
Convert the given Model field lookup to a GraphQL type.

Arguments:

`lookup: str`: The lookup to convert.

`default_type: type`: Default python type to use for the lookup.

`many: bool`: Whether the lookup is for a field that contains a list of objects or not.
"""

convert_to_bad_lookups: FunctionDispatcher[set[str]] = FunctionDispatcher()
"""
The output of `.get_lookups()` may include lookups that don't actually work or are undesirable
for the field. This function can be used to register these lookups per model field so that
FilterSet autogeneration can avoid generating Filters for these lookups.

Arguments:

`field: ModelField`: The Django Model field to look at.
"""

convert_to_default_value: FunctionDispatcher[Any] = FunctionDispatcher()
"""
Convert the given reference to a default value for an Input.
Returns `Undefined` if the reference doesn't have a default value.

Arguments:

`ref: Any`: The reference to convert to a default value.
"""

convert_to_description: FunctionDispatcher[str | None] = FunctionDispatcher()
"""
Convert the given convert.

Arguments:

`ref: Any`: The reference to parse description from.
"""

convert_to_entrypoint_resolver: FunctionDispatcher[GraphQLFieldResolver] = FunctionDispatcher()
"""
Convert the given reference to a GraphQL field resolver for an Entrypoint.

Arguments:

`ref: Any`: The reference to convert.

`caller: Entrypoint`: The Entrypoint instance that is calling this function.
"""

convert_to_field_complexity: FunctionDispatcher[int] = FunctionDispatcher()
"""
Determine the complexity of resolving the given reference.

Arguments:

`ref: Any`: The reference to look at.

`caller: Field`: The Field instance that is calling this function.
"""

convert_to_field_ref: FunctionDispatcher[Any] = FunctionDispatcher()
"""
Convert the given value to a reference that Field can deal with.

Arguments:

`ref: Any`: The value to convert.

`caller: Field`: Field instance that is calling this function.
"""

convert_to_field_resolver: FunctionDispatcher[GraphQLFieldResolver] = FunctionDispatcher()
"""
Convert the given reference to a field resolver function for Field.

Arguments:

`ref: Any`: The reference to convert.

`caller: Field`: The Field instance that is calling this function.
"""

convert_to_filter_ref: FunctionDispatcher[Any] = FunctionDispatcher()
"""
Convert the given value to a reference that Filter can deal with.

Arguments:

`ref: Any`: The value to convert.

`caller: Filter`: The Filter instance that is calling this function.
"""

convert_to_filter_resolver: FunctionDispatcher[GraphQLFilterResolver] = FunctionDispatcher()
"""
Convert the given reference to a filter resolver function for Filter.

Arguments:

`ref: Any`: The reference to convert.

`caller: Filter`: The Filter instance that is calling this function.
"""

convert_to_graphql_argument_map: FunctionDispatcher[GraphQLArgumentMap] = FunctionDispatcher()
"""
Parse a GraphQLArgumentMap from the given Entrypoint or Field reference.

Arguments:

`ref: Any`: The reference to convert.

`many: bool`: Whether the argument map is for a list field.

`entrypoint: bool = False`: (Optional) Whether the argument map is for an entrypoint.
"""

convert_to_graphql_type: FunctionDispatcher[GraphQLInputType | GraphQLOutputType] = FunctionDispatcher()
"""
Convert a given reference to a GraphQL input or output type.

Arguments:

`ref: Any`: The reference to convert.

`model: type[Model]`: The Django Model associated with the reference.

`is_input: bool = False`: (Optional) Whether the converted type should be an input or output type.
"""

convert_to_input_ref: FunctionDispatcher[Any] = FunctionDispatcher()
"""
Convert the given value to a reference that Input can deal with.

Arguments:

`ref: Any`: The value to convert.

`caller: Input`: The Input instance that is calling this function.
"""

convert_to_order_ref: FunctionDispatcher[Any] = FunctionDispatcher()
"""
Convert the given value to a reference that Order can deal with.

Arguments:

`ref: Any`: The value to convert.

`caller: Order`: The Order instance that is calling this function.
"""

convert_to_python_type: FunctionDispatcher[type] = FunctionDispatcher()
"""
Convert the given value to a python type.

Arguments:

`ref: Any`: The reference to convert.

`is_input: bool = False`: (Optional) Whether the type is for an input or output.
"""

extend_expression: FunctionDispatcher[DjangoExpression] = FunctionDispatcher()
"""
Rewrite an expression so that any containing lookups are referenced through the given field.

Arguments:

`expression: DjangoExpression`: The expression to extend.

`field_name: str`: Name of the field to extend the lookup to.
"""

is_field_nullable: FunctionDispatcher[bool] = FunctionDispatcher()
"""
Determine whether the given reference indicates a nullable Field or not.

Arguments:

`ref: Any`: The reference to check.

`caller: Field`: The Field instance that is calling this function.
"""

is_input_hidden: FunctionDispatcher[bool] = FunctionDispatcher()
"""
Determine whether the given reference indicates a hidden Input or not.

Arguments:

`ref: Any`: The reference to check.

`caller: Input`: The Input instance that is calling this function.
"""

is_input_only: FunctionDispatcher[bool] = FunctionDispatcher()
"""
Determine whether the given reference is indicates an input-only Input or not.

Arguments:

`ref: Any`: The reference to check.

`caller: Input`: The Input instance that is calling this function.
"""

is_input_required: FunctionDispatcher[bool] = FunctionDispatcher()
"""
Determine whether the give reference indicates a required Input or not.

Arguments:

`ref: Any`: The reference to check.

`caller: Input`: The Input instance that is calling this function.
"""

is_many: FunctionDispatcher[bool] = FunctionDispatcher()
"""
Determine whether the given reference indicates a list of objects or not.

Arguments:

`ref: Any`: The reference to look at.

`model: type[Model]`: The Django Model associated with the reference.

`name: str`: A name associated with the reference (e.g. field name)
"""


def convert_to_filter_lookups(ref: SupportsLookup, *, path: str = "") -> set[str]:
    """
    Find all lookups reachable from the given reference.
    This includes lookups for any transforms registered for the reference.
    """
    lookups: set[str] = set()
    for name, expr in _get_lookups_and_transforms(ref).items():
        # No need to include 'exact' lookup for nested lookups since the parent lookup does the same thing
        if path and name == "exact":
            continue

        lookup_name = f"{path}{LOOKUP_SEP}{name}" if path else name

        lookups.add(lookup_name)

        if has_callable_attribute(expr, "get_lookups"):
            lookups |= convert_to_filter_lookups(expr, path=lookup_name)  # type: ignore[arg-type]

    return lookups


def _get_lookups_and_transforms(ref: SupportsLookup) -> dict[str, type[Lookup | Transform]]:
    """
    Get all lookups and transforms for the given reference, including its 'output_field', if it has one.
    Exclude regex lookups and 'bad' lookups registered with 'get_bad_lookups'.
    """
    from django.contrib.contenttypes.fields import GenericForeignKey

    # Cannot do lookups on GenericForeignKeys
    if isinstance(ref, GenericForeignKey):
        return {}

    lookups: dict[str, type[Lookup | Transform]] = copy(ref.get_lookups())

    if hasattr(ref, "output_field") and isinstance(ref.output_field, Field):
        for name in _get_lookups_and_transforms(ref.output_field):
            existing_lookup = lookups.get(name)
            if existing_lookup is not None:
                continue

            lookup: type[Lookup | Transform] | None = ref.output_field.get_lookups().get(name, None)
            if lookup is None:  # pragma: no cover
                lookups.pop(name, None)
                continue

            # Don't include transforms for 'TruncDate' and 'TruncTime', since those are only registered
            # on 'DateTimeField', which already has all the lookups of 'DateField' and 'TimeField'.
            # This way the created 'FilterSet' will not be quite so verbose.
            if ref in {TruncDate, TruncTime} and is_subclass(lookup, Transform):
                continue

            lookups[name] = lookup

    # Don't allow regex inputs from users
    lookups.pop("iregex", None)
    lookups.pop("regex", None)

    for bad_lookup in convert_to_bad_lookups(ref):
        lookups.pop(bad_lookup, None)

    return lookups
