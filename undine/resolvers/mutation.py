from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Generic

from django.db import transaction  # noqa: ICN003
from django.db.models import Q
from graphql import Undefined

from undine.exceptions import GraphQLMissingLookupFieldError, GraphQLModelConstraintViolationError
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.model_utils import convert_integrity_errors, get_default_manager, get_instance_or_raise
from undine.utils.mutation_tree import mutate

from .query import QueryTypeManyResolver, QueryTypeSingleResolver

if TYPE_CHECKING:
    from undine import Entrypoint, MutationType
    from undine.typing import GQLInfo

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
    """Resolves a mutation for creating a model instance using."""

    mutation_type: type[MutationType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        model = self.mutation_type.__model__
        query_type = self.mutation_type.__query_type__()

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instance = mutate(data, model=model, info=info, mutation_type=self.mutation_type)

        resolver: QueryTypeSingleResolver[TModel] = QueryTypeSingleResolver(
            query_type=query_type,
            entrypoint=self.entrypoint,
        )
        return resolver(root, info, pk=instance.pk)


@dataclasses.dataclass(frozen=True, slots=True)
class UpdateResolver(Generic[TModel]):
    """Resolves a mutation for updating a model instance."""

    mutation_type: type[MutationType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        model = self.mutation_type.__model__
        query_type = self.mutation_type.__query_type__()

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        value = data.get("pk", Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=model, key="pk")

        instance = mutate(data, model=model, info=info, mutation_type=self.mutation_type)

        resolver: QueryTypeSingleResolver[TModel] = QueryTypeSingleResolver(
            query_type=query_type,
            entrypoint=self.entrypoint,
        )
        return resolver(root, info, pk=instance.pk)


@dataclasses.dataclass(frozen=True, slots=True)
class DeleteResolver(Generic[TModel]):
    """Resolves a mutation for deleting a model instance."""

    mutation_type: type[MutationType]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> SimpleNamespace:
        model = self.mutation_type.__model__

        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pk = input_data.get("pk", Undefined)
        if pk is Undefined:
            raise GraphQLMissingLookupFieldError(model=model, key="pk")

        instance = get_instance_or_raise(model=model, pk=pk)

        self.mutation_type.__before__(instance=instance, info=info, input_data=input_data)

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            instance.delete()

        self.mutation_type.__after__(instance=instance, info=info, previous_data={})

        return SimpleNamespace(pk=pk)


# Bulk


@dataclasses.dataclass(frozen=True, slots=True)
class BulkCreateResolver(Generic[TModel]):
    """Resolves a bulk create mutation for creating a list of model instances."""

    mutation_type: type[MutationType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        model = self.mutation_type.__model__
        query_type = self.mutation_type.__query_type__()

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instances = mutate(data, model=model, info=info, mutation_type=self.mutation_type)

        resolver: QueryTypeManyResolver[TModel] = QueryTypeManyResolver(
            query_type=query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return resolver(root, info)


@dataclasses.dataclass(frozen=True, slots=True)
class BulkUpdateResolver(Generic[TModel]):
    """Resolves a bulk update mutation for updating a list of model instances."""

    mutation_type: type[MutationType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        model = self.mutation_type.__model__
        query_type = self.mutation_type.__query_type__()

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instances = mutate(data, model=model, info=info, mutation_type=self.mutation_type)

        resolver: QueryTypeManyResolver[TModel] = QueryTypeManyResolver(
            query_type=query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return resolver(root, info)


@dataclasses.dataclass(frozen=True, slots=True)
class BulkDeleteResolver(Generic[TModel]):
    """Resolves a bulk delete mutation for deleting a list of model instances."""

    mutation_type: type[MutationType]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[SimpleNamespace]:
        model = self.mutation_type.__model__

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pks = [input_data["pk"] for input_data in data if "pk" in input_data]

        queryset = get_default_manager(model).filter(pk__in=pks)
        instances = list(queryset)

        for instance in instances:
            self.mutation_type.__before__(instance=instance, info=info, input_data={})

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            queryset.delete()

        for instance in instances:
            self.mutation_type.__after__(instance=instance, info=info, previous_data={})

        return [SimpleNamespace(pk=pk) for pk in pks]


# Custom


@dataclasses.dataclass(frozen=True, slots=True)
class CustomResolver:
    """Resolves a custom mutation a model instance."""

    mutation_type: type[MutationType]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        self.mutation_type.__before__(instance=root, info=info, input_data=input_data)

        with transaction.atomic(), convert_integrity_errors(GraphQLModelConstraintViolationError):
            response = self.mutation_type.__mutate__(root, info, input_data)

        self.mutation_type.__after__(instance=root, info=info, previous_data={})

        return response
