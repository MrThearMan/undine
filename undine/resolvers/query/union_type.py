from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from undine.settings import undine_settings
from undine.utils.graphql.utils import get_field_path_identifier

from .union_query import (
    apply_shared_filters,
    apply_shared_order,
    apply_union_cursor_filters,
    check_permissions,
    check_permissions_async,
    connection_from_page,
    empty_connection,
    fetch_union_instances,
    fetch_union_instances_async,
    limit_union_query,
    optimize_members,
    union_count,
    union_count_async,
    union_page,
    union_page_query,
)

if TYPE_CHECKING:
    from django.db.models import Model
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, UnionType
    from undine.relay import Connection
    from undine.typing import ConnectionDict, GQLInfo


__all__ = [
    "UnionTypeConnectionResolver",
    "UnionTypeResolver",
]


@dataclasses.dataclass(frozen=True, slots=True)
class UnionTypeResolver:
    """Resolves a union type to all of its members."""

    union_type: type[UnionType]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[Model]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[Model]:
        query_types = self.union_type.__query_types_by_model__.values()
        members = optimize_members(query_types, info, build_descriptors=False, **kwargs)
        if not members:
            return []

        matches_anything = apply_shared_filters(self.union_type.__filterset__, members, info)
        if not matches_anything:
            return []

        ordering = apply_shared_order(self.union_type.__orderset__, members, info)
        union_queryset = union_page_query(members, ordering)
        union_queryset = limit_union_query(union_queryset, self.entrypoint, info)

        instances = fetch_union_instances(members, union_queryset)
        check_permissions(
            entrypoint=self.entrypoint,
            root=root,
            info=info,
            members=members,
            instances=instances,
        )
        return instances

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[Model]:
        query_types = self.union_type.__query_types_by_model__.values()
        members = optimize_members(query_types, info, build_descriptors=False, **kwargs)
        if not members:
            return []

        matches_anything = apply_shared_filters(self.union_type.__filterset__, members, info)
        if not matches_anything:
            return []

        ordering = apply_shared_order(self.union_type.__orderset__, members, info)
        union_queryset = union_page_query(members, ordering)
        union_queryset = limit_union_query(union_queryset, self.entrypoint, info)

        instances = await fetch_union_instances_async(members, union_queryset)
        await check_permissions_async(
            entrypoint=self.entrypoint,
            root=root,
            info=info,
            members=members,
            instances=instances,
        )
        return instances


@dataclasses.dataclass(frozen=True, slots=True)
class UnionTypeConnectionResolver:
    """Resolves a connection of union type items."""

    connection: Connection
    entrypoint: Entrypoint

    @property
    def union_type(self) -> type[UnionType]:
        return self.connection.union_type  # type: ignore[return-value]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[ConnectionDict[Model]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[Model]:
        query_types = self.union_type.__query_types_by_model__.values()
        members = optimize_members(query_types, info, build_descriptors=True, **kwargs)

        # Pagination adds the primary key to every member's optimizations,
        # so a connection always selects something from every member.
        if not members:  # pragma: no cover
            return empty_connection()

        matches_anything = apply_shared_filters(self.union_type.__filterset__, members, info)
        if not matches_anything:
            return empty_connection()

        ordering = apply_shared_order(self.union_type.__orderset__, members, info)

        key = get_field_path_identifier(info.path)
        pagination = info.context.undine_internal.connection_handler_storage[key]

        # The total count must be resolved before the cursor filters are applied,
        # otherwise it would only count the rows remaining after the cursor.
        if pagination.requires_total_count:
            pagination.total_count = union_count(members)

        apply_union_cursor_filters(members, ordering, pagination)

        union_queryset = union_page_query(members, ordering)
        union_queryset = pagination.apply_pagination(union_queryset, info)

        instances = fetch_union_instances(members, union_queryset)
        check_permissions(
            entrypoint=self.entrypoint,
            root=root,
            info=info,
            members=members,
            instances=instances,
        )

        page = union_page(instances, pagination, ordering)
        return connection_from_page(page)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[Model]:
        query_types = self.union_type.__query_types_by_model__.values()
        members = optimize_members(query_types, info, build_descriptors=True, **kwargs)
        if not members:  # pragma: no cover
            return empty_connection()

        matches_anything = apply_shared_filters(self.union_type.__filterset__, members, info)
        if not matches_anything:
            return empty_connection()

        ordering = apply_shared_order(self.union_type.__orderset__, members, info)

        key = get_field_path_identifier(info.path)
        pagination = info.context.undine_internal.connection_handler_storage[key]

        # The total count must be resolved before the cursor filters are applied,
        # otherwise it would only count the rows remaining after the cursor.
        if pagination.requires_total_count:
            pagination.total_count = await union_count_async(members)

        apply_union_cursor_filters(members, ordering, pagination)

        union_queryset = union_page_query(members, ordering)
        union_queryset = pagination.apply_pagination(union_queryset, info)

        instances = await fetch_union_instances_async(members, union_queryset)
        await check_permissions_async(
            entrypoint=self.entrypoint,
            root=root,
            info=info,
            members=members,
            instances=instances,
        )

        page = union_page(instances, pagination, ordering)
        return connection_from_page(page)
