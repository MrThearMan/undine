from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from graphql import (
    FieldNode,
    FragmentSpreadNode,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLUnionType,
    InlineFragmentNode,
)

from undine.dataclasses import CacheControlResults
from undine.exceptions import NoRequestCaching
from undine.settings import undine_settings
from undine.utils.graphql.undine_extensions import (
    get_undine_entrypoint,
    get_undine_field,
    get_undine_interface_field,
    get_undine_interface_type,
    get_undine_query_type,
    get_undine_union_type,
)
from undine.utils.graphql.utils import get_field_def, get_underlying_type
from undine.utils.visibility import (
    has_interface_type_visibility_override,
    has_member_visibility,
    has_query_type_visibility_override,
    has_union_type_visibility_override,
)

if TYPE_CHECKING:
    from graphql import (
        FragmentDefinitionNode,
        GraphQLCompositeType,
        GraphQLField,
        OperationDefinitionNode,
        SelectionNode,
    )

    from undine import Entrypoint, Field, InterfaceField

__all__ = [
    "RequestCacheCalculator",
]


class RequestCacheCalculator:
    """Calculated the cache time allowed for the given operation."""

    def __init__(self, operation: OperationDefinitionNode, fragments: dict[str, FragmentDefinitionNode]) -> None:
        self.cache_time: int = -1
        self.cache_per_user: bool = False

        self.operation = operation
        self.fragments = fragments
        self.visited_fragments: set[str] = set()

    def run(self) -> CacheControlResults:
        root_type: GraphQLObjectType = undine_settings.SCHEMA.get_root_type(self.operation.operation)  # type: ignore[assignment]

        with suppress(NoRequestCaching):
            for selection in self.operation.selection_set.selections:
                self.calculate_cache_time(root_type, selection)

        return CacheControlResults(cache_time=max(self.cache_time, 0), cache_per_user=self.cache_per_user)

    def calculate_cache_time(self, parent_type: GraphQLCompositeType, selection: SelectionNode) -> None:
        match selection:
            case FieldNode():
                field = get_field_def(undine_settings.SCHEMA, parent_type, selection)  # type: ignore[arg-type]
                field_type: GraphQLCompositeType = get_underlying_type(field.type)  # type: ignore[assignment]
                self.parse_cache_time(field)
                if selection.selection_set is not None:
                    for sel in selection.selection_set.selections:
                        self.calculate_cache_time(field_type, sel)

            case InlineFragmentNode():
                type_condition = selection.type_condition
                if type_condition is None:
                    for sel in selection.selection_set.selections:
                        self.calculate_cache_time(parent_type, sel)
                    return

                fragment_name = type_condition.name.value
                fragment_type: GraphQLObjectType = undine_settings.SCHEMA.get_type(fragment_name)  # type: ignore[assignment]
                for sel in selection.selection_set.selections:
                    self.calculate_cache_time(fragment_type, sel)

            case FragmentSpreadNode():  # pragma: no branch
                if selection.name.value not in self.visited_fragments:
                    self.visited_fragments.add(selection.name.value)
                    fragment = self.fragments.get(selection.name.value)
                    if fragment is not None:
                        for sel in fragment.selection_set.selections:
                            self.calculate_cache_time(parent_type, sel)

    def parse_cache_time(self, field: GraphQLField) -> None:
        undine_entrypoint = get_undine_entrypoint(field)
        if undine_entrypoint is not None:
            self.parse_cache_time_from_entrypoint(undine_entrypoint, field)
            return

        undine_field = get_undine_field(field)
        if undine_field is not None:
            self.parse_cache_time_from_field(undine_field, field)
            return

        undine_interface_field = get_undine_interface_field(field)
        if undine_interface_field is not None:
            self.parse_cache_time_from_interface_field(undine_interface_field, field)
            return

    def parse_cache_time_from_entrypoint(self, entrypoint: Entrypoint, field: GraphQLField) -> None:
        if has_member_visibility(entrypoint):
            self.cache_per_user = True

        if entrypoint.cache_time is not None:
            self.cache_time = entrypoint.cache_time
            self.cache_per_user |= entrypoint.cache_per_user

        field_type: GraphQLCompositeType = get_underlying_type(field.type)  # type: ignore[assignment]
        self.parse_cache_time_from_type(field_type, is_entrypoint=True)

        if self.cache_time <= 0:
            raise NoRequestCaching

    def parse_cache_time_from_field(self, undine_field: Field, field: GraphQLField) -> None:
        if has_member_visibility(undine_field):
            self.cache_per_user = True

        if undine_field.cache_time is not None:
            self.cache_time = min(self.cache_time, undine_field.cache_time)
            self.cache_per_user |= undine_field.cache_per_user
        else:
            field_type: GraphQLCompositeType = get_underlying_type(field.type)  # type: ignore[assignment]
            self.parse_cache_time_from_type(field_type)

        if self.cache_time <= 0:
            raise NoRequestCaching

    def parse_cache_time_from_interface_field(self, interface_field: InterfaceField, field: GraphQLField) -> None:
        if has_member_visibility(interface_field):
            self.cache_per_user = True

        if interface_field.cache_time is not None:
            self.cache_time = min(self.cache_time, interface_field.cache_time)
            self.cache_per_user |= interface_field.cache_per_user
        else:
            field_type: GraphQLCompositeType = get_underlying_type(field.type)  # type: ignore[assignment]
            self.parse_cache_time_from_type(field_type)

        if self.cache_time <= 0:
            raise NoRequestCaching

    def parse_cache_time_from_type(self, field_type: GraphQLCompositeType, *, is_entrypoint: bool = False) -> None:  # noqa: C901
        match field_type:
            case GraphQLObjectType():
                query_type = get_undine_query_type(field_type)
                if query_type is not None:
                    if not is_entrypoint and query_type.__cache_time__ is not None:
                        self.cache_time = min(self.cache_time, query_type.__cache_time__)
                        self.cache_per_user |= query_type.__cache_per_user__

                    if has_query_type_visibility_override(query_type):
                        self.cache_per_user = True

            case GraphQLInterfaceType():
                interface_type = get_undine_interface_type(field_type)
                if interface_type is not None:
                    if not is_entrypoint and interface_type.__cache_time__ is not None:
                        self.cache_time = min(self.cache_time, interface_type.__cache_time__)
                        self.cache_per_user |= interface_type.__cache_per_user__

                    if has_interface_type_visibility_override(interface_type):
                        self.cache_per_user = True

            case GraphQLUnionType():
                union_type = get_undine_union_type(field_type)
                if union_type is not None:
                    if not is_entrypoint and union_type.__cache_time__ is not None:
                        self.cache_time = min(self.cache_time, union_type.__cache_time__)
                        self.cache_per_user |= union_type.__cache_per_user__

                    if has_union_type_visibility_override(union_type):
                        self.cache_per_user = True
