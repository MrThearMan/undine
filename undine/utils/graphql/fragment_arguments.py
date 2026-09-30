from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.execution.collect_fields import FragmentDetails, collect_fields, collect_subfields
from graphql.execution.get_variable_signature import get_variable_signature

from undine.settings import undine_settings

if TYPE_CHECKING:
    from graphql import GraphQLObjectType
    from graphql.execution.collect_fields import FieldDetailsList
    from graphql.execution.get_variable_signature import GraphQLVariableSignature
    from graphql.execution.values import FragmentVariableValues
    from graphql.pyutils import Path

    from undine.typing import GQLInfo

__all__ = [
    "get_collected_field_node_ids",
    "get_fragment_variable_values",
    "uses_fragment_arguments",
]


def uses_fragment_arguments(info: GQLInfo) -> bool:
    """Does the GraphQL document of the operation define fragments with variables?"""
    if not undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS:
        return False
    return any(fragment.variable_definitions for fragment in info.fragments.values())


def get_fragment_variable_values(info: GQLInfo) -> FragmentVariableValues | None:
    """Get the values of the fragment variables in scope for the field in the given GraphQL resolve info."""
    if not uses_fragment_arguments(info):
        return None

    field_details_list = _get_field_details_list(info)
    return field_details_list[0].fragment_variable_values


def get_collected_field_node_ids(info: GQLInfo, runtime_type: GraphQLObjectType) -> set[int]:
    """
    Get the identities of the field nodes that are selected from the field in the given GraphQL resolve info
    when its value has the given runtime type. Fields excluded by `@skip` or `@include` are not included.
    """
    field_details_list = _get_field_details_list(info)
    collected = collect_subfields(
        info.schema,
        _get_fragment_details(info),
        info.variable_values,
        info.operation,
        runtime_type,
        field_details_list,
    )
    return {
        id(field_details.node)
        for collected_field_details_list in collected.grouped_field_set.values()
        for field_details in collected_field_details_list
    }


def _get_field_details_list(info: GQLInfo) -> FieldDetailsList:
    """
    Collect the fields from the root of the operation along the path in the given GraphQL resolve info,
    the same way the executor does, so that the fragment variables in scope for the field are known.
    """
    segments: list[tuple[str, str]] = []

    path: Path | None = info.path
    while path is not None:
        # List indices don't change the selections, so only field keys are followed.
        if isinstance(path.key, str):
            segments.append((path.key, path.typename))  # type: ignore[arg-type]
        path = path.prev

    segments.reverse()
    return _collect_field_details_list(info, tuple(segments))


def _collect_field_details_list(info: GQLInfo, segments: tuple[tuple[str, str], ...]) -> FieldDetailsList:
    cache = info.context.undine_internal.field_details_lists

    field_details_list = cache.get(segments)
    if field_details_list is not None:
        return field_details_list

    *parent_segments, (key, typename) = segments
    parent_type: GraphQLObjectType = info.schema.get_type(typename)  # type: ignore[assignment]
    fragments = _get_fragment_details(info)

    if parent_segments:
        parent_field_details_list = _collect_field_details_list(info, tuple(parent_segments))
        collected = collect_subfields(
            info.schema,
            fragments,
            info.variable_values,
            info.operation,
            parent_type,
            parent_field_details_list,
        )
    else:
        collected = collect_fields(info.schema, fragments, info.variable_values, parent_type, info.operation)

    field_details_list = collected.grouped_field_set[key]
    cache[segments] = field_details_list
    return field_details_list


def _get_fragment_details(info: GQLInfo) -> dict[str, FragmentDetails]:
    internal = info.context.undine_internal
    if internal.fragment_details is not None:
        return internal.fragment_details

    fragments: dict[str, FragmentDetails] = {}
    for name, definition in info.fragments.items():
        variable_signatures: dict[str, GraphQLVariableSignature] | None = None
        if definition.variable_definitions:
            variable_signatures = {}
            for variable_definition in definition.variable_definitions:
                # The executor has already rejected the operation if any of the signatures were invalid.
                signature: GraphQLVariableSignature = get_variable_signature(info.schema, variable_definition)  # type: ignore[assignment]
                variable_signatures[signature.name] = signature

        fragments[name] = FragmentDetails(definition, variable_signatures)

    internal.fragment_details = fragments
    return fragments
