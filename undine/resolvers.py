"""
Contains different types of resolvers for GraphQL operations.
Resolvers must be callables with the following signature:

(root: Root, info: GQLInfo, **kwargs: Any) -> Any
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable, Generic, Self

from graphql import GraphQLResolveInfo, Undefined

from undine.errors.exceptions import GraphQLMissingLookupFieldError, GraphQLPermissionDeniedError
from undine.middleware import MutationMiddlewareHandler
from undine.optimizer.optimizer import QueryOptimizer
from undine.settings import undine_settings
from undine.typing import GQLInfo, RelatedManager, TModel
from undine.utils.bulk_mutation_handler import BulkMutationHandler
from undine.utils.model_utils import get_instance_or_raise
from undine.utils.mutation_handler import MutationHandler
from undine.utils.reflection import get_signature

if TYPE_CHECKING:
    from types import FunctionType

    from django.db import models

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
    "UpdateResolver",
]


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
class QueryTypeSingleRelatedFieldResolver(ModelSingleRelatedFieldResolver):
    """Resolves a single related field pointing to another QueryType."""

    query_type: type[QueryType]

    def __call__(self, instance: models.Model, info: GQLInfo, **kwargs: Any) -> Any:
        # Cannot use zero-arg `super()` due to an issue with `slots=True` dataclasses.
        rel_instance = super(QueryTypeSingleRelatedFieldResolver, self).__call__(instance, info, **kwargs)  # noqa: UP008

        if not self.field.skip_querytype_perms and not self.query_type.__permission_single__(rel_instance, info):
            raise GraphQLPermissionDeniedError
        return rel_instance


@dataclasses.dataclass(frozen=True, slots=True)
class QueryTypeManyRelatedFieldResolver(ModelManyRelatedFieldResolver):
    """Resolves a many related field pointing to another QueryType."""

    query_type: type[QueryType]

    def __call__(self, instance: models.Model, info: GQLInfo, **kwargs: Any) -> Any:
        # Cannot use zero-arg `super()` due to an issue with `slots=True` dataclasses.
        queryset = super(QueryTypeManyRelatedFieldResolver, self).__call__(instance, info, **kwargs)  # noqa: UP008

        if not self.field.skip_querytype_perms and not self.query_type.__permission_many__(queryset, info):
            raise GraphQLPermissionDeniedError
        return queryset


@dataclasses.dataclass(frozen=True, slots=True)
class ModelSingleResolver:
    """Top-level resolver for fetching a single model object."""

    query_type: type[QueryType]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> models.Model | None:
        queryset = self.query_type.__get_queryset__(info).filter(**kwargs)
        optimizer = QueryOptimizer(query_type=self.query_type, info=info)
        optimized_queryset = optimizer.optimize(queryset)
        # Shouldn't use .first(), as it can apply additional ordering, which would cancel the optimization.
        # The queryset should have the right model instance, since we started by filtering by its pk,
        # so we can just pick that out of the result cache (if it hasn't been filtered out).
        instance = next(iter(optimized_queryset), None)
        if not self.query_type.__permission_single__(instance, info):
            raise GraphQLPermissionDeniedError
        return instance


@dataclasses.dataclass(frozen=True, slots=True)
class ModelManyResolver:
    """Top-level resolver for fetching a set of model objects."""

    query_type: type[QueryType]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> models.QuerySet:
        queryset = self.query_type.__get_queryset__(info)
        optimizer = QueryOptimizer(query_type=self.query_type, info=info)
        optimized_queryset = optimizer.optimize(queryset)
        if not self.query_type.__permission_many__(optimized_queryset, info):
            raise GraphQLPermissionDeniedError
        return optimized_queryset


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
class CreateResolver(Generic[TModel]):
    """
    Resolves a mutation for creating a model instance using 'MutationHandler.create'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> TModel:
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        handler = MutationHandler(model=self.mutation_type.__model__)

        with MutationMiddlewareHandler(
            mutation_type=self.mutation_type,
            info=info,
            input_data=data,
        ):
            return handler.create(data)


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

        with MutationMiddlewareHandler(
            mutation_type=self.mutation_type,
            info=info,
            input_data=data,
        ):
            return handler.create_many(
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

        with MutationMiddlewareHandler(
            mutation_type=self.mutation_type,
            info=info,
            input_data=data,
            instance=instance,
        ):
            return handler.update(instance, data)


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

        with MutationMiddlewareHandler(
            mutation_type=self.mutation_type,
            info=info,
            input_data=data,
            instances=instances,
        ):
            return handler.update_many(data, instances, lookup_field=lookup_field, batch_size=batch_size)


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

        with MutationMiddlewareHandler(
            mutation_type=self.mutation_type,
            info=info,
            input_data=data,
            instance=instance,
        ):
            instance.delete()

        return {undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: True}


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

        instances = model._meta.default_manager.filter(pk__in=pks)

        with MutationMiddlewareHandler(
            mutation_type=self.mutation_type,
            info=info,
            input_data={},
            instances=list(instances),
        ):
            instances.delete()

        return {undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: True}


@dataclasses.dataclass(frozen=True, slots=True)
class CustomResolver:
    """
    Resolves a custom mutation a model instance using 'mutation_type.__mutate__'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Any:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        with MutationMiddlewareHandler(
            mutation_type=self.mutation_type,
            info=info,
            input_data=input_data,
        ):
            return self.mutation_type.__mutate__(root, info, input_data)
