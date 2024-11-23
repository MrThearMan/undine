"""
Contains different types of resolvers for GraphQL operations.
Resolvers must be callables with the following signature:

(root: Root, info: GQLInfo, **kwargs: Any) -> Any
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Self

from django.db import models, transaction
from graphql import GraphQLResolveInfo, Undefined

from undine.errors.error_handlers import handle_integrity_errors
from undine.errors.exceptions import GraphQLInvalidManyRelatedFieldError, GraphQLMissingLookupFieldError
from undine.middleware import MutationMiddlewareHandler
from undine.settings import undine_settings
from undine.typing import GQLInfo, RelatedManagerProtocol
from undine.utils.model_utils import get_instance_or_raise
from undine.utils.mutation_handler import MutationHandler
from undine.utils.reflection import get_signature

if TYPE_CHECKING:
    from types import FunctionType

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
        value: RelatedManagerProtocol | None = getattr(model, self.name, None)
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
class CreateResolver:
    """
    Resolves a mutation for creating a model instance using 'MutationHandler.create'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Model:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        with (
            transaction.atomic(),
            handle_integrity_errors(),
            MutationMiddlewareHandler(self.mutation_type, info, input_data),
        ):
            return MutationHandler(model=self.mutation_type.__model__).create(input_data)


@dataclass(frozen=True, slots=True)
class BulkCreateResolver:
    """
    Resolves a bulk create mutation for creating a list of model instances using `manager.bulk_create()`.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[models.Model]:
        return self.mutation_type.__model__

    @property
    def manager(self) -> models.Manager:
        return self.model._meta.default_manager

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> list[Model]:
        input_data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        batch_size: int | None = kwargs.get("batch_size")
        ignore_conflicts: bool = kwargs.get("ignore_conflicts", False)
        update_conflicts: bool = kwargs.get("update_conflicts", False)
        update_fields: list[str] | None = kwargs.get("update_fields")
        unique_fields: list[str] | None = kwargs.get("unique_fields")

        objs = [self.model(**data) for data in input_data]

        with (
            transaction.atomic(),
            handle_integrity_errors(),
            MutationMiddlewareHandler(self.mutation_type, info, input_data),
        ):
            return self.manager.bulk_create(
                objs,
                batch_size=batch_size,
                ignore_conflicts=ignore_conflicts,
                update_conflicts=update_conflicts,
                update_fields=update_fields,
                unique_fields=unique_fields,
            )


@dataclass(frozen=True, slots=True)
class UpdateResolver:
    """
    Resolves a mutation for updating a model instance using 'MutationHandler.update'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[models.Model]:
        return self.mutation_type.__model__

    @property
    def lookup_field(self) -> str:
        return self.mutation_type.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Model:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        value = input_data.pop(self.lookup_field, Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key=self.lookup_field)

        instance = get_instance_or_raise(model=self.model, key=self.lookup_field, value=value)

        with (
            transaction.atomic(),
            handle_integrity_errors(),
            MutationMiddlewareHandler(self.mutation_type, info, input_data, instance),
        ):
            return MutationHandler(model=self.mutation_type.__model__).update(instance, input_data)


@dataclass(frozen=True, slots=True)
class BulkUpdateResolver:
    """
    Resolves a bulk update mutation for updating a list of model instances using `manager.bulk_update()`.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[models.Model]:
        return self.mutation_type.__model__

    @property
    def manager(self) -> models.Manager:
        return self.model._meta.default_manager

    @property
    def lookup_field(self) -> str:
        return self.mutation_type.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> list[Model]:
        input_data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        batch_size: int | None = kwargs.get("batch_size")

        objs = [self.model(**data) for data in input_data]
        # Update all fields except the lookup field.
        fields = list({field for data in input_data for field in data if field != self.lookup_field})

        with (
            transaction.atomic(),
            handle_integrity_errors(),
            MutationMiddlewareHandler(self.mutation_type, info, input_data),
        ):
            self.manager.bulk_update(objs, fields, batch_size=batch_size)
            return objs


@dataclass(frozen=True, slots=True)
class DeleteResolver:
    """
    Resolves a mutation for deleting a model instance using 'model.delete'.
    Runs all defined mutation middlewares. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[models.Model]:
        return self.mutation_type.__model__

    @property
    def lookup_field(self) -> str:
        return self.mutation_type.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> dict[str, bool]:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]
        value = input_data.get(self.lookup_field, Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key=self.lookup_field)

        instance = get_instance_or_raise(model=self.model, key=self.lookup_field, value=value)

        with (
            transaction.atomic(),
            handle_integrity_errors(),
            MutationMiddlewareHandler(self.mutation_type, info, input_data, instance),
        ):
            instance.delete()

        return {undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: True}


@dataclass(frozen=True, slots=True)
class BulkDeleteResolver:
    """
    Resolves a bulk delete mutation for deleting a list of model instances using `qs.delete()`.
    Runs MutationType's '__validate__' method. Mutation is run in a transaction.
    """

    mutation_type: type[MutationType]

    @property
    def model(self) -> type[models.Model]:
        return self.mutation_type.__model__

    @property
    def queryset(self) -> models.Manager:
        return self.model._meta.default_manager

    @property
    def lookup_field(self) -> str:
        return self.mutation_type.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> dict[str, bool]:
        input_data: list[Any] = kwargs[undine_settings.MUTATION_INPUT_KEY]

        with (
            transaction.atomic(),
            handle_integrity_errors(),
        ):
            self.mutation_type.__validate__(info=info, input_data=input_data)
            self.queryset.filter(pk__in=input_data).delete()
            self.mutation_type.__post_handle__(info=info, input_data=input_data)

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

        with (
            transaction.atomic(),
            handle_integrity_errors(),
            MutationMiddlewareHandler(self.mutation_type, info, input_data),
        ):
            return self.mutation_type.__mutate__(root, info, input_data)
