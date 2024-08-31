from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from undine.errors import TypeRegistryDuplicateError, TypeRegistryMissingTypeError
from undine.utils.lazy import lazy

if TYPE_CHECKING:
    from django.db import models

    from undine import ModelGQLType


__all__ = [
    "TYPE_REGISTRY",
]


class _TypeRegistry:
    """
    Maps Django model classes to their corresponding `ModelGQLTypes`.
    This allows deferring the creation of field resolvers for related fields,
    which would use a `ModelGQLType` that is not created when the field is defined.
    """

    _singleton: _TypeRegistry

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if not hasattr(cls, "_singleton"):
            cls._singleton = super().__new__(cls, *args, **kwargs)
        return cls._singleton

    def __init__(self) -> None:
        self.__registry: dict[type[models.Model], type[ModelGQLType]] = {}

    def __getitem__(self, model: type[models.Model]) -> type[ModelGQLType]:
        try:
            return self.__registry[model]
        except KeyError as error:
            raise TypeRegistryMissingTypeError(model=model) from error

    def __setitem__(self, model: type[models.Model], graphql_type: type[ModelGQLType]) -> None:
        if model in self.__registry:
            raise TypeRegistryDuplicateError(model=model, graphql_type=TYPE_REGISTRY[model])
        self.__registry[model] = graphql_type

    def get_deferred(self, model: type[models.Model]) -> type[ModelGQLType]:
        """Defer accessing given model's ModelGQLType from the registry until it's used for the first time."""

        def wrapper() -> type[ModelGQLType]:
            return self[model]

        return lazy.create(wrapper)


TYPE_REGISTRY = _TypeRegistry()
