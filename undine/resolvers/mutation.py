from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Generic

from graphql import Undefined

from undine.errors.exceptions import GraphQLMissingLookupFieldError
from undine.middleware.mutation import MutationMiddlewareHandler
from undine.settings import undine_settings
from undine.typing import GQLInfo, TModel
from undine.utils.model_utils import get_instance_or_raise
from undine.utils.mutation_handlers import BulkMutationHandler, MutationHandler

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

    from undine import MutationType
    from undine.typing import Root

__all__ = [
    "BulkCreateResolver",
    "BulkDeleteResolver",
    "BulkUpdateResolver",
    "CreateResolver",
    "CustomResolver",
    "DeleteResolver",
    "UpdateResolver",
]


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
class UpdateResolver(Generic[TModel]):
    """
    Resolves a mutation for updating a model instance using 'MutationHandler.update'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Model:
        model = self.mutation_type.__model__

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        value = data.pop("pk", Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=model, key="pk")

        instance = get_instance_or_raise(model=model, key="pk", value=value)

        handler = MutationHandler(model=model)
        middlewares = MutationMiddlewareHandler(info, data, mutation_type=self.mutation_type, instance=instance)

        return middlewares.wrap(handler.update)(instance, data)


@dataclasses.dataclass(frozen=True, slots=True)
class DeleteResolver(Generic[TModel]):
    """
    Resolves a mutation for deleting a model instance using 'model.delete'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> dict[str, bool]:
        model = self.mutation_type.__model__

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        value = data.get("pk", Undefined)

        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=model, key="pk")

        instance = get_instance_or_raise(model=model, key="pk", value=value)

        middlewares = MutationMiddlewareHandler(info, data, mutation_type=self.mutation_type, instance=instance)

        middlewares.wrap(self.delete)(instance)

        return {undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: True}

    def delete(self, instance: Model) -> None:
        instance.delete()


# Bulk


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
class BulkUpdateResolver(Generic[TModel]):
    """
    Resolves a bulk update mutation for updating a list of model instances using `manager.bulk_update()`.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        model = self.mutation_type.__model__

        batch_size: int | None = kwargs.get("batch_size")

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        pks = [item["pk"] for item in data]

        instances: list[Model] = list(model._meta.default_manager.filter(pk__in=pks))

        handler = BulkMutationHandler(model=model)
        middlewares = MutationMiddlewareHandler(info, data, mutation_type=self.mutation_type, instances=instances)

        return middlewares.wrap(handler.update_many)(
            data,
            instances,
            batch_size=batch_size,
        )


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

    def delete(self, queryset: QuerySet) -> None:
        queryset.delete()


# Custom


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
