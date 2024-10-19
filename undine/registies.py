"""Contains a class for registering `QueryType`s for reuse based on their Django model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from django.db import models
from graphql import GraphQLEnumType

from undine.errors.exceptions import RegistryDuplicateError, TypeRegistryMissingTypeError
from undine.utils.reflection import get_instance_name

if TYPE_CHECKING:
    # Avoid circular imports by importing types only, and using 'ForwardRefs' (=quotes).
    from undine.query import QueryType
    from undine.utils.mutation_handler import MutationHandler  # noqa: F401


__all__ = [
    "QUERY_TYPE_REGISTRY",
]


From = TypeVar("From")
To = TypeVar("To")


class Registry(Generic[From, To]):
    """
    A registry that stores mappings from one type to another.
    Verifies that a value for a given key is only registered once.
    """

    def __class_getitem__(cls, _: tuple[From, To]) -> type[Registry[From, To]]:
        return cls

    def __init__(self) -> None:
        self.__registry: dict[From, To] = {}
        self.__name = get_instance_name()

    def __getitem__(self, key: From) -> To:
        try:
            return self.__registry[key]
        except KeyError as error:
            raise TypeRegistryMissingTypeError(registry_name=self.__name, key=key) from error

    def __setitem__(self, key: From, value: To) -> None:
        if key in self.__registry:
            raise RegistryDuplicateError(key=key, value=self.__registry[key], registry_name=self.__name)
        self.__registry[key] = value

    def __contains__(self, key: From) -> bool:
        return key in self.__registry

    def clear(self) -> None:
        self.__registry.clear()


QUERY_TYPE_REGISTRY = Registry[type[models.Model], type["QueryType"]]()
"""
Maps Django model classes to their corresponding `QueryTypes`.
This allows deferring the creation of field resolvers for related fields,
which would use a `QueryType` that is not created when the field is defined.
"""

GRAPHQL_ENUM_REGISTRY = Registry[str, GraphQLEnumType]()
"""
Caches created GraphQL Enums by their names, so that
they can be reused when converting the same field multiple times, since
a GraphQL Schema cannot contain multiple types with the same name.
"""
