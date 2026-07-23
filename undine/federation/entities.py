from __future__ import annotations

import dataclasses
import inspect
from functools import partial
from typing import TYPE_CHECKING, Any

from graphql import GraphQLAbstractType  # noqa: TC002

from undine import Entrypoint, QueryType
from undine.federation.directives import KeyDirective
from undine.federation.federation_type import FederationType
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_union
from undine.utils.graphql.utils import pre_evaluate_request_user
from undine.utils.model_utils import get_instance_by_field_or_raise, get_instance_by_field_or_raise_async

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db.models import Model
    from graphql import GraphQLUnionType

    from undine.entrypoint import RootType
    from undine.typing import GQLInfo


__all__ = [
    "make_entities_entrypoint",
]


def make_entities_entrypoint(
    query: type[RootType],
    query_types: list[type[QueryType]],
    federation_types: list[type[FederationType]],
) -> Entrypoint:
    entity_union = _build_entity_union(query_types, federation_types)

    entities_by_typename: dict[str, type[QueryType | FederationType]] = {}
    for query_type in query_types:
        entities_by_typename[query_type.__schema_name__] = query_type
    for federation_type in federation_types:
        entities_by_typename[federation_type.__schema_name__] = federation_type

    ref = EntitiesRef(entities_by_typename=entities_by_typename, entity_union=entity_union)

    entrypoint = Entrypoint(
        ref,
        schema_name="_entities",
        extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
    )
    entrypoint.__connect__(query, "_entities")
    return entrypoint


def _build_entity_union(
    query_types: list[type[QueryType]],
    federation_types: list[type[FederationType]],
) -> GraphQLUnionType:
    query_type_output_types = (query_type.__output_type__() for query_type in query_types)
    federation_type_output_types = (federation_type.__output_type__() for federation_type in federation_types)
    types = [*query_type_output_types, *federation_type_output_types]

    model_to_typename = {query_type.__model__: query_type.__schema_name__ for query_type in query_types}

    def resolve_type(instance: Model | FederationType, info: GQLInfo, abstract_type: GraphQLAbstractType) -> str | None:
        if isinstance(instance, FederationType):
            return type(instance).__schema_name__
        return model_to_typename.get(type(instance))

    return get_or_create_graphql_union(
        name="_Entity",
        types=types,
        resolve_type=resolve_type,
        extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
    )


@dataclasses.dataclass(slots=True, kw_only=True, frozen=True, eq=False)
class EntitiesRef:
    entities_by_typename: dict[str, type[QueryType | FederationType]]
    entity_union: GraphQLUnionType


@dataclasses.dataclass(frozen=True, slots=True)
class EntitiesResolver:
    """Resolves the Apollo Federation `Query._entities` field."""

    ref: EntitiesRef

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        representations: list[dict[str, Any]] = kwargs["representations"]
        if undine_settings.ASYNC:
            return self._run_async(root, info, representations)
        return self._run_sync(root, info, representations)

    def _run_sync(
        self,
        root: Any,
        info: GQLInfo,
        representations: list[dict[str, Any]],
    ) -> list[Any]:
        return [self._resolve_one_sync(rep, info) for rep in representations]

    async def _run_async(
        self,
        root: Any,
        info: GQLInfo,
        representations: list[dict[str, Any]],
    ) -> list[Any]:
        await pre_evaluate_request_user(info)
        return [await self._resolve_one_async(rep, info) for rep in representations]

    def _resolve_one_sync(self, representation: dict[str, Any], info: GQLInfo) -> Any:
        entity_cls = self._lookup(representation)
        if entity_cls is None:
            return None

        if issubclass(entity_cls, QueryType):
            return self._resolve_query_type_reference(entity_cls, representation, info)

        if issubclass(entity_cls, FederationType):
            return self._resolve_federation_type_reference(entity_cls, representation, info)

        msg = f"Unknown entity type: {entity_cls}"  # pragma: no cover
        raise TypeError(msg)  # pragma: no cover

    async def _resolve_one_async(self, representation: dict[str, Any], info: GQLInfo) -> Any:
        entity_cls = self._lookup(representation)
        if entity_cls is None:
            return None

        if issubclass(entity_cls, QueryType):
            return await self._resolve_query_type_reference_async(entity_cls, representation, info)

        if issubclass(entity_cls, FederationType):
            return await self._resolve_federation_type_reference_async(entity_cls, representation, info)

        msg = f"Unknown entity type: {entity_cls}"  # pragma: no cover
        raise TypeError(msg)  # pragma: no cover

    def _resolve_query_type_reference(
        self,
        query_type: type[QueryType],
        representation: dict[str, Any],
        info: GQLInfo,
    ) -> Model | None | Exception:
        default = partial(self._default_query_type_reference_resolver, query_type)
        resolve_reference: Callable[[dict, GQLInfo], Any] = getattr(query_type, "__resolve_reference__", default)

        try:
            instance = resolve_reference(representation, info)
            if instance is None:
                return None

            query_type.__permissions__(instance, info)

        except Exception as error:  # noqa: BLE001
            return error

        return instance

    async def _resolve_query_type_reference_async(
        self,
        query_type: type[QueryType],
        representation: dict[str, Any],
        info: GQLInfo,
    ) -> Model | None | Exception:
        default = partial(self._default_query_type_reference_resolver_async, query_type)
        resolve_reference: Callable[[dict, GQLInfo], Any] = getattr(query_type, "__resolve_reference__", default)

        try:
            if inspect.iscoroutinefunction(resolve_reference):
                instance = await resolve_reference(representation, info)
            else:
                instance = resolve_reference(representation, info)

            if instance is None:
                return None

            if inspect.iscoroutinefunction(query_type.__permissions__):
                await query_type.__permissions__(instance, info)
            else:
                query_type.__permissions__(instance, info)

        except Exception as error:  # noqa: BLE001
            return error

        return instance

    def _resolve_federation_type_reference(
        self,
        federation_type: type[FederationType],
        representation: dict[str, Any],
        info: GQLInfo,
    ) -> FederationType | None | Exception:
        default = partial(self._default_federation_type_reference_resolver, federation_type)
        resolve_reference: Callable[[dict, GQLInfo], Any] = getattr(federation_type, "__resolve_reference__", default)

        try:
            instance = resolve_reference(representation, info)
            if instance is None:
                return None

            federation_type.__permissions__(instance, info)

        except Exception as error:  # noqa: BLE001
            return error

        return instance

    async def _resolve_federation_type_reference_async(
        self,
        federation_type: type[FederationType],
        representation: dict[str, Any],
        info: GQLInfo,
    ) -> FederationType | None | Exception:
        default = partial(self._default_federation_type_reference_resolver, federation_type)
        resolve_reference: Callable[[dict, GQLInfo], Any] = getattr(federation_type, "__resolve_reference__", default)

        try:
            if inspect.iscoroutinefunction(resolve_reference):
                instance = await resolve_reference(representation, info)
            else:
                instance = resolve_reference(representation, info)

            if instance is None:
                return None

            if inspect.iscoroutinefunction(federation_type.__permissions__):
                await federation_type.__permissions__(instance, info)
            else:
                federation_type.__permissions__(instance, info)

        except Exception as error:  # noqa: BLE001
            return error

        return instance

    def _lookup(self, representation: dict[str, Any]) -> type[QueryType | FederationType] | None:
        typename = representation.get("__typename")
        if not isinstance(typename, str):
            return None
        return self.ref.entities_by_typename.get(typename)

    def _default_query_type_reference_resolver(
        self,
        query_type: type[QueryType],
        representation: dict[str, Any],
        info: GQLInfo,
    ) -> Model:
        name, value = self._find_queryset_filter_pair(query_type, representation)
        queryset = query_type.__get_queryset__(info)
        return get_instance_by_field_or_raise(queryset=queryset, field_name=name, value=value)

    async def _default_query_type_reference_resolver_async(
        self,
        query_type: type[QueryType],
        representation: dict[str, Any],
        info: GQLInfo,
    ) -> Model:
        name, value = self._find_queryset_filter_pair(query_type, representation)
        queryset = query_type.__get_queryset__(info)
        return await get_instance_by_field_or_raise_async(queryset=queryset, field_name=name, value=value)

    def _default_federation_type_reference_resolver(
        self,
        federation_type: type[FederationType],
        representation: dict[str, Any],
        info: GQLInfo,
    ) -> FederationType:
        kwargs = {
            field.name: representation[field.schema_name]
            for field in federation_type.__field_map__.values()
            if field.schema_name in representation
        }
        return federation_type(**kwargs)

    def _find_queryset_filter_pair(
        self,
        query_type: type[QueryType],
        representation: dict[str, Any],
    ) -> tuple[str, Any]:
        key_directive = self._first_resolvable_key_directive(query_type)
        key_field = key_directive.__parameters__["fields"]
        key_value = representation.get(key_field)

        if key_value is None:  # pragma: no cover
            msg = f"Key field '{key_field}' not found in given representation"
            raise RuntimeError(msg)

        gen = (field.field_name for field in query_type.__field_map__.values() if field.schema_name == key_field)
        field_name = next(gen, None)

        if field_name is None:  # pragma: no cover
            msg = f"Field '{key_field}' not found in '{query_type.__name__}'"
            raise RuntimeError(msg)

        return field_name, key_value

    def _first_resolvable_key_directive(self, query_type: type[QueryType]) -> KeyDirective:
        for directive in query_type.__directives__:
            if isinstance(directive, KeyDirective) and directive.__parameters__["resolvable"]:
                return directive

        msg = f"No resolvable '@KeyDirective' on '{query_type.__name__}'."  # pragma: no cover
        raise RuntimeError(msg)  # pragma: no cover
