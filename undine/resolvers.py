"""
Contains different types of resolvers for GraphQL operations.
Resolvers must be callables with the following signature:

(root: Root, info: GQLInfo, **kwargs: Any) -> Any
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, Self

from graphql import GraphQLResolveInfo, Undefined

from undine.errors.exceptions import GraphQLInvalidManyRelatedFieldError, GraphQLMissingLookupFieldError
from undine.middleware import MutationMiddlewareHandler
from undine.settings import undine_settings
from undine.typing import GQLInfo, RelatedManager, TModel
from undine.utils.bulk_mutation_handler import BulkMutationHandler
from undine.utils.model_utils import get_instance_or_raise
from undine.utils.mutation_handler import MutationHandler
from undine.utils.reflection import get_signature

if TYPE_CHECKING:
    from types import FunctionType

    from django.db import models
    from django.db.models import Model

    from undine.mutation import MutationType
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
    "ModelManyRelatedResolver",
    "UpdateResolver",
]


@dataclass(frozen=True, slots=True)
class ModelFieldResolver:
    """Resolves a model field to a value by attribute access."""

    name: str

    def __call__(self, model: models.Model, info: GQLInfo, **kwargs: Any) -> Any:
        return getattr(model, self.name, None)


@dataclass(frozen=True, slots=True)
class ModelManyRelatedResolver:
    """Resolves a many-related model field to its queryset."""

    name: str

    def __call__(self, model: models.Model, info: GQLInfo, **kwargs: Any) -> models.QuerySet:
        value: RelatedManager | None = getattr(model, self.name, None)
        try:
            return value.get_queryset()
        except Exception as error:
            raise GraphQLInvalidManyRelatedFieldError(model=type(model), field_name=self.name, value=value) from error


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class CreateResolver(Generic[TModel]):
    """
    Resolves a mutation for creating a model instance using 'MutationHandler.create'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> TModel:
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        handler = MutationHandler(model=self.model)

        with MutationMiddlewareHandler(mutation_type=self.mutation_type, info=info, input_data=data):
            return handler.create(data)


@dataclass(frozen=True, slots=True)
class BulkCreateResolver(Generic[TModel]):
    """
    Resolves a bulk create mutation for creating a list of model instances using `manager.bulk_create()`.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        batch_size: int | None = kwargs.get("batch_size")
        ignore_conflicts: bool = kwargs.get("ignore_conflicts", False)
        update_conflicts: bool = kwargs.get("update_conflicts", False)
        update_fields: list[str] | None = kwargs.get("update_fields")
        unique_fields: list[str] | None = kwargs.get("unique_fields")

        handler = BulkMutationHandler(model=self.model)

        with MutationMiddlewareHandler(mutation_type=self.mutation_type, info=info, input_data=data):
            return handler.create_many(
                data,
                batch_size=batch_size,
                ignore_conflicts=ignore_conflicts,
                update_conflicts=update_conflicts,
                update_fields=update_fields,
                unique_fields=unique_fields,
            )


@dataclass(frozen=True, slots=True)
class UpdateResolver(Generic[TModel]):
    """
    Resolves a mutation for updating a model instance using 'MutationHandler.update'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__

    @property
    def lookup_field(self) -> str:
        return self.mutation_type.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Model:
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        value = data.pop(self.lookup_field, Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key=self.lookup_field)

        instance = get_instance_or_raise(model=self.model, key=self.lookup_field, value=value)
        handler = MutationHandler(model=self.model)

        with MutationMiddlewareHandler(mutation_type=self.mutation_type, info=info, input_data=data, instance=instance):
            return handler.update(instance, data)


@dataclass(frozen=True, slots=True)
class BulkUpdateResolver(Generic[TModel]):
    """
    Resolves a bulk update mutation for updating a list of model instances using `manager.bulk_update()`.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__

    @property
    def lookup_field(self) -> str:
        return self.mutation_type.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        batch_size: int | None = kwargs.get("batch_size")

        handler = BulkMutationHandler(model=self.model)

        with MutationMiddlewareHandler(mutation_type=self.mutation_type, info=info, input_data=data):
            return handler.update_many(data, lookup_field=self.lookup_field, batch_size=batch_size)


@dataclass(frozen=True, slots=True)
class DeleteResolver(Generic[TModel]):
    """
    Resolves a mutation for deleting a model instance using 'model.delete'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__

    @property
    def lookup_field(self) -> str:
        return self.mutation_type.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> dict[str, bool]:
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        value = data.get(self.lookup_field, Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key=self.lookup_field)

        instance = get_instance_or_raise(model=self.model, key=self.lookup_field, value=value)

        with MutationMiddlewareHandler(mutation_type=self.mutation_type, info=info, input_data=data, instance=instance):
            instance.delete()

        return {undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: True}


@dataclass(frozen=True, slots=True)
class BulkDeleteResolver(Generic[TModel]):
    """
    Resolves a bulk delete mutation for deleting a list of model instances using `qs.delete()`.
    Runs MutationType's '__validate__' method. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__

    @property
    def manager(self) -> RelatedManager[TModel]:
        return self.model._meta.default_manager  # type: ignore[return-value]

    @property
    def lookup_field(self) -> str:
        return self.mutation_type.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> dict[str, bool]:
        input_data: list[Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        with MutationMiddlewareHandler(mutation_type=self.mutation_type, info=info, input_data={}):
            self.manager.filter(pk__in=input_data).delete()

        return {undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: True}


@dataclass(frozen=True, slots=True)
class CustomResolver:
    """
    Resolves a custom mutation a model instance using 'mutation_type.__mutate__'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Any:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        with MutationMiddlewareHandler(mutation_type=self.mutation_type, info=info, input_data=input_data):
            return self.mutation_type.__mutate__(root, info, input_data)
