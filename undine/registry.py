"""Contains a class for registering `QueryType`s for reuse based on their Django model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from undine.errors.exceptions import TypeRegistryDuplicateError, TypeRegistryMissingTypeError

if TYPE_CHECKING:
    from django.db import models

    from undine.query import QueryType

__all__ = [
    "TYPE_REGISTRY",
]


class _TypeRegistry:
    """
    Maps Django model classes to their corresponding `QueryTypes`.
    This allows deferring the creation of field resolvers for related fields,
    which would use a `QueryType` that is not created when the field is defined.
    """

    _singleton: _TypeRegistry

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if not hasattr(cls, "_singleton"):
            cls._singleton = super().__new__(cls, *args, **kwargs)
        return cls._singleton

    def __init__(self) -> None:
        self.__registry: dict[type[models.Model], type[QueryType]] = {}

    def __getitem__(self, model: type[models.Model]) -> type[QueryType]:
        try:
            return self.__registry[model]
        except KeyError as error:
            raise TypeRegistryMissingTypeError(model=model) from error

    def __setitem__(self, model: type[models.Model], graphql_type: type[QueryType]) -> None:
        if model in self.__registry:
            raise TypeRegistryDuplicateError(model=model, graphql_type=TYPE_REGISTRY[model])
        self.__registry[model] = graphql_type

    def __contains__(self, model: type[models.Model]) -> bool:
        return model in self.__registry

    def clear(self) -> None:
        self.__registry.clear()


TYPE_REGISTRY = _TypeRegistry()
