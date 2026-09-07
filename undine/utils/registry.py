from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from undine.exceptions import RegistryDuplicateError, RegistryMissingTypeError
from undine.utils.reflection import get_instance_name

if TYPE_CHECKING:
    from collections.abc import ItemsView, Iterator, KeysView, ValuesView

__all__ = [
    "Registry",
]


From = TypeVar("From")
To = TypeVar("To")


class Registry(Generic[From, To]):
    """
    A registry for values that need to be globally available.
    Verifies that a value for a given key is only registered once.
    """

    def __init__(self) -> None:
        self.__registry: dict[From, To] = {}
        self.__name = get_instance_name()

    def __getitem__(self, key: From) -> To:
        try:
            return self.__registry[key]
        except KeyError as error:
            raise RegistryMissingTypeError(registry_name=self.__name, key=key) from error

    def __setitem__(self, key: From, value: To) -> None:
        if key in self.__registry:
            raise RegistryDuplicateError(key=key, value=self.__registry[key], registry_name=self.__name)
        self.__registry[key] = value

    def __contains__(self, key: From) -> bool:
        return key in self.__registry

    def __iter__(self) -> Iterator[From]:
        return iter(self.__registry)

    def keys(self) -> KeysView[From]:
        return self.__registry.keys()

    def values(self) -> ValuesView[To]:
        return self.__registry.values()

    def items(self) -> ItemsView[From, To]:
        return self.__registry.items()

    def clear(self) -> None:
        self.__registry.clear()
