"""
Contains different types of resolvers for GraphQL operations.
Resolvers must be callables with the following signature:

(root: Root, info: GQLInfo, **kwargs: Any) -> Any
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable, Generic, Self

from django.db import models
from graphql import GraphQLError, GraphQLID, GraphQLObjectType, GraphQLResolveInfo, Undefined

from undine.errors.exceptions import GraphQLMissingLookupFieldError, GraphQLPermissionDeniedError
from undine.middleware.mutation import MutationMiddlewareHandler
from undine.middleware.query import QueryMiddlewareHandler
from undine.optimizer.ast import get_underlying_type
from undine.optimizer.optimizer import QueryOptimizer
from undine.optimizer.prefetch_hack import evaluate_in_context
from undine.relay import Node, from_global_id, offset_to_cursor, to_global_id
from undine.settings import undine_settings
from undine.typing import ConnectionDict, GQLInfo, NodeDict, PageInfoDict, RelatedManager, TModel
from undine.utils.bulk_mutation_handler import BulkMutationHandler
from undine.utils.model_utils import get_instance_or_raise
from undine.utils.mutation_handler import MutationHandler
from undine.utils.reflection import get_signature

if TYPE_CHECKING:
    from types import FunctionType

    from undine import Field, MutationType, QueryType
    from undine.typing import Root

__all__ = [
    "BulkCreateResolver",
    "BulkDeleteResolver",
    "BulkUpdateResolver",
    "CreateResolver",
    "CustomResolver",
    "DeleteResolver",
    "FunctionResolver",
    "ModelFieldResolver",
    "ModelManyRelatedFieldResolver",
    "NodeResolver",
    "UpdateResolver",
]


@dataclasses.dataclass(frozen=True, slots=True)
class FunctionResolver:
    """Resolves a GraphQL field using the given function."""

    func: FunctionType | Callable[..., Any]
    root_param: str | None = None
    info_param: str | None = None

    @classmethod
    def adapt(cls, func: FunctionType | Callable[..., Any], *, depth: int = 0) -> Self:
        """
        Create the appropriate resolver for a function based on its signature.
        Leave out the `root` parameter from static functions, and only include the
        `info` parameter if the function has a parameter of the `GraphQLResolveInfo` type.

        Note that the `root` is always the first parameter, and the matching happens
        by it's name, which can be configured with `RESOLVER_ROOT_PARAM_NAME`.
        `self` and `cls` are always accepted root parameter names, since they are the
        conventions for instance and class methods respectively.
        """
        sig = get_signature(func, depth=depth + 1)

        root_param: str | None = None
        info_param: str | None = None
        for i, param in enumerate(sig.parameters.values()):
            if i == 0 and param.name in {"self", "cls", undine_settings.RESOLVER_ROOT_PARAM_NAME}:
                root_param = param.name

            elif param.annotation in {GQLInfo, GraphQLResolveInfo}:
                info_param = param.name
                break

        return cls(func=func, root_param=root_param, info_param=info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info
        return self.func(**kwargs)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelSingleResolver(Generic[TModel]):
    """Top-level resolver for fetching a single model object."""

    query_type: type[QueryType]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        middlewares = QueryMiddlewareHandler(root, info, query_type=self.query_type)

        @middlewares.wrap
        def getter() -> TModel | None:
            queryset = self.query_type.__get_queryset__(info).filter(**kwargs)
            optimizer = QueryOptimizer(query_type=self.query_type, info=info)
            optimized_queryset = optimizer.optimize(queryset)
            instances = evaluate_in_context(optimized_queryset)
            return next(iter(instances), None)

        return getter()


@dataclasses.dataclass(frozen=True, slots=True)
class ModelManyResolver(Generic[TModel]):
    """Top-level resolver for fetching a set of model objects."""

    query_type: type[QueryType]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        middlewares = QueryMiddlewareHandler(root, info, query_type=self.query_type)

        @middlewares.wrap
        def getter() -> list[TModel]:
            queryset = self.query_type.__get_queryset__(info)
            optimizer = QueryOptimizer(query_type=self.query_type, info=info)
            optimized_queryset = optimizer.optimize(queryset)
            return evaluate_in_context(optimized_queryset)

        return getter()


@dataclasses.dataclass(frozen=True, slots=True)
class ModelFieldResolver:
    """Resolves a model field to a value by attribute access."""

    field: Field

    def __call__(self, instance: models.Model, info: GQLInfo, **kwargs: Any) -> Any:
        if self.field.permissions_func is not None and not self.field.permissions_func(self.field, info, instance):
            raise GraphQLPermissionDeniedError

        return getattr(instance, self.field.field_name, None)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelSingleRelatedFieldResolver:
    """Resolves single-related model field to its value."""

    field: Field

    def __call__(self, instance: models.Model, info: GQLInfo, **kwargs: Any) -> models.Model | None:
        if self.field.permissions_func is not None and not self.field.permissions_func(self.field, info, instance):
            raise GraphQLPermissionDeniedError

        return getattr(instance, self.field.field_name, None)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelManyRelatedFieldResolver:
    """Resolves a many-related model field to its queryset."""

    field: Field

    def __call__(self, instance: models.Model, info: GQLInfo, **kwargs: Any) -> models.QuerySet:
        if self.field.permissions_func is not None and not self.field.permissions_func(self.field, info, instance):
            raise GraphQLPermissionDeniedError

        manager: RelatedManager = getattr(instance, self.field.field_name)
        return manager.get_queryset()


@dataclasses.dataclass(frozen=True, slots=True)
class QueryTypeSingleRelatedFieldResolver(Generic[TModel]):
    """Resolves a single related field pointing to another QueryType."""

    query_type: type[QueryType]
    field: Field

    def __call__(self, instance: models.Model, info: GQLInfo, **kwargs: Any) -> TModel | None:
        middlewares = QueryMiddlewareHandler(instance, info, query_type=self.query_type, field=self.field)

        @middlewares.wrap
        def getter() -> TModel | None:
            return getattr(instance, self.field.field_name, None)

        return getter()


@dataclasses.dataclass(frozen=True, slots=True)
class QueryTypeManyRelatedFieldResolver(Generic[TModel]):
    """Resolves a many related field pointing to another QueryType."""

    query_type: type[QueryType]
    field: Field

    def __call__(self, instance: models.Model, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        middlewares = QueryMiddlewareHandler(instance, info, query_type=self.query_type, field=self.field)

        @middlewares.wrap
        def getter() -> list[TModel]:
            field_name = getattr(info.field_nodes[0].alias, "value", self.field.field_name)
            result: RelatedManager | list[models.Model] = getattr(instance, field_name)

            if isinstance(result, models.Manager):
                return list(result.get_queryset())
            return result

        return getter()


@dataclasses.dataclass(frozen=True, slots=True)
class GlobalIDResolver:
    """Resolves a model primary key as a Global ID."""

    typename: str

    def __call__(self, root: models.Model, info: GQLInfo, **kwargs: Any) -> str:
        return to_global_id(self.typename, root.pk)


@dataclasses.dataclass(frozen=True, slots=True)
class NodeResolver:
    """Resolves a model instance though a Global ID."""

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        typename, object_id = from_global_id(kwargs["id"])

        object_type: GraphQLObjectType | None = info.schema.get_type(typename)
        if object_type is None:
            msg = f"Object type '{typename}' does not exist in schema."
            raise GraphQLError(msg)

        if Node not in object_type.interfaces:
            msg = f"Object type '{typename}' must implement the 'Node' interface."
            raise GraphQLError(msg)

        query_type: type[QueryType] | None = object_type.extensions.get(undine_settings.QUERY_TYPE_EXTENSIONS_KEY)
        if query_type is None:
            msg = f"Cannot find undine QueryType from object type '{typename}'."
            raise GraphQLError(msg)

        field: Field | None = query_type.__field_map__.get("id")
        if field is None:
            msg = f"The object type '{typename}' doesn't have an 'id' field."
            raise GraphQLError(msg)

        field_type = get_underlying_type(field.get_field_type())
        if field_type is not GraphQLID:
            msg = (
                f"The 'id' field of the object type '{typename}' must be of type '{GraphQLID.name}' "
                f"to comply with the 'Node' interface."
            )
            raise GraphQLError(msg)

        resolver = ModelSingleResolver(query_type=query_type)
        return resolver(root, info, pk=object_id)


@dataclasses.dataclass(frozen=True, slots=True)
class ConnectionResolver(Generic[TModel]):
    """Resolves a connection of a given query type."""

    query_type: type[QueryType]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        middlewares = QueryMiddlewareHandler(root, info, query_type=self.query_type)

        total_count: int | None = 0
        start: int = 0
        stop: int = 0

        @middlewares.wrap
        def getter() -> list[TModel]:
            nonlocal total_count, start, stop

            queryset = self.query_type.__get_queryset__(info)
            optimizer = QueryOptimizer(query_type=self.query_type, info=info)
            optimized_queryset = optimizer.optimize(queryset)

            total_count = optimized_queryset._hints.get(undine_settings.CONNECTION_TOTAL_COUNT_KEY, None)
            start = optimized_queryset._hints[undine_settings.CONNECTION_START_INDEX_KEY]
            stop = optimized_queryset._hints[undine_settings.CONNECTION_STOP_INDEX_KEY]

            return evaluate_in_context(optimized_queryset)

        instances = getter()

        edges = [
            NodeDict(
                cursor=offset_to_cursor(start + index),
                node=instance,
            )
            for index, instance in enumerate(instances)
        ]
        return ConnectionDict(
            totalCount=total_count,
            pageInfo=PageInfoDict(
                hasNextPage=stop < total_count if total_count is not None else True,
                hasPreviousPage=start > 0,
                startCursor=None if not edges else edges[0]["cursor"],
                endCursor=None if not edges else edges[-1]["cursor"],
            ),
            edges=edges,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class NestedConnectionResolver(Generic[TModel]):
    """Resolves a nested connection of a given query type from the given field."""

    query_type: type[QueryType]
    field: Field

    def __call__(self, instance: models.Model, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        middlewares = QueryMiddlewareHandler(instance, info, query_type=self.query_type, field=self.field)

        total_count: int | None = 0
        start: int = 0
        stop: int = 0

        @middlewares.wrap
        def getter() -> list[TModel]:
            field_name = getattr(info.field_nodes[0].alias, "value", self.field.field_name)
            result: RelatedManager[TModel] | list[TModel] = getattr(instance, field_name)

            if isinstance(result, models.Manager):
                optimized_queryset = result.get_queryset()
                result = list(optimized_queryset)

            if result:
                nonlocal total_count, start, stop

                total_count = getattr(result[0], undine_settings.CONNECTION_TOTAL_COUNT_KEY, None)
                start = getattr(result[0], undine_settings.CONNECTION_START_INDEX_KEY)
                stop = getattr(result[0], undine_settings.CONNECTION_STOP_INDEX_KEY)

            return instances

        instances = getter()

        edges = [
            NodeDict(
                cursor=offset_to_cursor(start + index),
                node=instance,
            )
            for index, instance in enumerate(instances)
        ]
        return ConnectionDict(
            totalCount=total_count,
            pageInfo=PageInfoDict(
                hasNextPage=stop < total_count if total_count is not None else True,
                hasPreviousPage=start > 0,
                startCursor=None if not edges else edges[0]["cursor"],
                endCursor=None if not edges else edges[-1]["cursor"],
            ),
            edges=edges,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class CreateResolver(Generic[TModel]):
    """
    Resolves a mutation for creating a model instance using 'MutationHandler.create'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> TModel:
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        handler = MutationHandler(model=self.mutation_type.__model__)
        middlewares = MutationMiddlewareHandler(info, data, mutation_type=self.mutation_type)

        return middlewares.wrap(handler.create)(data)


@dataclasses.dataclass(frozen=True, slots=True)
class BulkCreateResolver(Generic[TModel]):
    """
    Resolves a bulk create mutation for creating a list of model instances using `manager.bulk_create()`.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        model = self.mutation_type.__model__

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        batch_size: int | None = kwargs.get("batch_size")
        ignore_conflicts: bool = kwargs.get("ignore_conflicts", False)
        update_conflicts: bool = kwargs.get("update_conflicts", False)
        update_fields: list[str] | None = kwargs.get("update_fields")
        unique_fields: list[str] | None = kwargs.get("unique_fields")

        handler = BulkMutationHandler(model=model)
        middlewares = MutationMiddlewareHandler(info, data, mutation_type=self.mutation_type)

        return middlewares.wrap(handler.create_many)(
            data,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class UpdateResolver(Generic[TModel]):
    """
    Resolves a mutation for updating a model instance using 'MutationHandler.update'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> models.Model:
        model = self.mutation_type.__model__
        lookup_field = self.mutation_type.__lookup_field__

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        value = data.pop(lookup_field, Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=model, key=lookup_field)

        instance = get_instance_or_raise(model=model, key=lookup_field, value=value)

        handler = MutationHandler(model=model)
        middlewares = MutationMiddlewareHandler(info, data, mutation_type=self.mutation_type, instance=instance)

        return middlewares.wrap(handler.update)(instance, data)


@dataclasses.dataclass(frozen=True, slots=True)
class BulkUpdateResolver(Generic[TModel]):
    """
    Resolves a bulk update mutation for updating a list of model instances using `manager.bulk_update()`.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        model = self.mutation_type.__model__
        lookup_field = self.mutation_type.__lookup_field__

        batch_size: int | None = kwargs.get("batch_size")

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        pks = [item[lookup_field] for item in data]

        instances: list[models.Model] = list(model._meta.default_manager.filter(pk__in=pks))

        handler = BulkMutationHandler(model=model)
        middlewares = MutationMiddlewareHandler(info, data, mutation_type=self.mutation_type, instances=instances)

        return middlewares.wrap(handler.update_many)(
            data,
            instances,
            lookup_field=lookup_field,
            batch_size=batch_size,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class DeleteResolver(Generic[TModel]):
    """
    Resolves a mutation for deleting a model instance using 'model.delete'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> dict[str, bool]:
        model = self.mutation_type.__model__
        lookup_field = self.mutation_type.__lookup_field__

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        value = data.get(lookup_field, Undefined)

        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=model, key=lookup_field)

        instance = get_instance_or_raise(model=model, key=lookup_field, value=value)

        middlewares = MutationMiddlewareHandler(info, data, mutation_type=self.mutation_type, instance=instance)

        middlewares.wrap(self.delete)(instance)

        return {undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: True}

    def delete(self, instance: models.Model) -> None:
        instance.delete()


@dataclasses.dataclass(frozen=True, slots=True)
class BulkDeleteResolver(Generic[TModel]):
    """
    Resolves a bulk delete mutation for deleting a list of model instances using `qs.delete()`.
    Runs MutationType's '__validate__' method. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> dict[str, bool]:
        model = self.mutation_type.__model__

        pks: list[Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        queryset = model._meta.default_manager.filter(pk__in=pks)
        middlewares = MutationMiddlewareHandler(info, {}, mutation_type=self.mutation_type, instances=list(queryset))

        middlewares.wrap(self.delete)(queryset)

        return {undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: True}

    def delete(self, queryset: models.QuerySet) -> None:
        queryset.delete()


@dataclasses.dataclass(frozen=True, slots=True)
class CustomResolver:
    """
    Resolves a custom mutation a model instance using 'mutation_type.__mutate__'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Any:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        middlewares = MutationMiddlewareHandler(info, input_data, mutation_type=self.mutation_type)

        return middlewares.wrap(self.mutation_type.__mutate__)(root, info, input_data)
