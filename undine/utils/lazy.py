"""Contains a urility class for lazy evaluation of objects."""

from __future__ import annotations

import math
from copy import copy, deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, TypeVar

from undine.registies import QUERY_TYPE_REGISTRY
from undine.typing import RelatedField, empty
from undine.utils.model_utils import generic_relations_for_generic_foreign_key

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine.query import QueryType

__all__ = [
    "LazyQueryType",
    "LazyQueryTypeUnion",
    "lazy",
]

R = TypeVar("R")


@dataclass(frozen=True, slots=True)
class LazyQueryType:
    """Represents a lazily evaluated QueryType for a related field."""

    field: RelatedField

    def get_type(self) -> type[QueryType]:
        return QUERY_TYPE_REGISTRY[self.field.related_model]


@dataclass(frozen=True, slots=True)
class LazyQueryTypeUnion:
    """Represents a lazily evaluated QueryType for a related field."""

    field: GenericForeignKey

    def get_types(self) -> list[type[QueryType]]:
        return [
            QUERY_TYPE_REGISTRY[field.remote_field.related_model]
            for field in generic_relations_for_generic_foreign_key(self.field)
        ]


class lazy:  # noqa: N801
    """Object used for lazy evaluation of objects."""

    @classmethod
    def create(cls, target: Callable[[], R] | type[R], *args: Any, **kwargs: Any) -> R:
        """
        Creates a lazily evaluated object from the target callable or class.
        The target is then evaluated once when some operation is performed on
        the lazy object (there might be some cases where this does not work),
        and acts like it is the target callables return value
        or an instance of the target class.

        :param target: Callable or class to evaluate lazily.
        :param args: Positional arguments to pass to the target.
        :param kwargs: Keyword arguments to pass to the target.
        """
        self = cls()
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs
        self.__result = empty
        return self

    def __check_result(self) -> None:
        # Evaluates the target once.
        if self.__result is empty:
            self.__result = self.__target(*self.__args, **self.__kwargs)

    # Implement most magic methods to forward the calls to the result.

    def __getattr__(self, name: str) -> Any:
        self.__check_result()
        return getattr(self.__result, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ["_lazy__target", "_lazy__args", "_lazy__kwargs", "_lazy__result"]:
            super().__setattr__(name, value)
            return

        self.__check_result()
        setattr(self.__result, name, value)

    def __delattr__(self, name: str) -> None:
        self.__check_result()
        delattr(self.__result, name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.__check_result()
        return self.__result(*args, **kwargs)

    def __eq__(self, other: object) -> bool:
        self.__check_result()
        return self.__result == other

    def __hash__(self) -> int:
        self.__check_result()
        return hash(self.__result)

    def __repr__(self) -> str:
        self.__check_result()
        return repr(self.__result)

    def __str__(self) -> str:
        self.__check_result()
        return str(self.__result)

    def __bool__(self) -> bool:
        self.__check_result()
        return bool(self.__result)

    def __bytes__(self) -> bytes:
        self.__check_result()
        return bytes(self.__result)

    def __format__(self, format_spec: str) -> str:
        self.__check_result()
        return format(self.__result, format_spec)

    def __dir__(self) -> list[str]:
        self.__check_result()
        return dir(self.__result)

    def __lt__(self, other: Any) -> bool:
        self.__check_result()
        return self.__result < other

    def __le__(self, other: Any) -> bool:
        self.__check_result()
        return self.__result <= other

    def __gt__(self, other: Any) -> bool:
        self.__check_result()
        return self.__result > other

    def __ge__(self, other: Any) -> bool:
        self.__check_result()
        return self.__result >= other

    def __add__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result + other

    def __sub__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result - other

    def __mul__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result * other

    def __matmul__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result @ other

    def __truediv__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result / other

    def __floordiv__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result // other

    def __mod__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result % other

    def __divmod__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result.__divmod__(other)

    def __pow__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result**other

    def __lshift__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result << other

    def __rshift__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result >> other

    def __and__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result & other

    def __xor__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result ^ other

    def __or__(self, other: Any) -> Any:
        self.__check_result()
        return self.__result | other

    def __radd__(self, other: Any) -> Any:
        self.__check_result()
        return other + self.__result

    def __rsub__(self, other: Any) -> Any:
        self.__check_result()
        return other - self.__result

    def __rmul__(self, other: Any) -> Any:
        self.__check_result()
        return other * self.__result

    def __rmatmul__(self, other: Any) -> Any:
        self.__check_result()
        return other @ self.__result

    def __rtruediv__(self, other: Any) -> Any:
        self.__check_result()
        return other / self.__result

    def __rfloordiv__(self, other: Any) -> Any:
        self.__check_result()
        return other // self.__result

    def __rmod__(self, other: Any) -> Any:
        self.__check_result()
        return other % self.__result

    def __rdivmod__(self, other: object) -> Any:
        self.__check_result()
        return other.__rdivmod__(self.__result)

    def __neg__(self) -> Any:
        self.__check_result()
        return -self.__result

    def __pos__(self) -> Any:
        self.__check_result()
        return +self.__result

    def __abs__(self) -> Any:
        self.__check_result()
        return abs(self.__result)

    def __invert__(self) -> Any:
        self.__check_result()
        return ~self.__result

    def __round__(self, ndigits: int | None = None) -> Any:
        self.__check_result()
        return round(self.__result, ndigits)

    def __floor__(self) -> Any:
        self.__check_result()
        return math.floor(self.__result)

    def __ceil__(self) -> Any:
        self.__check_result()
        return math.ceil(self.__result)

    def __trunc__(self) -> Any:
        self.__check_result()
        return math.trunc(self.__result)

    def __float__(self) -> float:
        self.__check_result()
        return float(self.__result)

    def __int__(self) -> int:
        self.__check_result()
        return int(self.__result)

    def __complex__(self) -> complex:
        self.__check_result()
        return complex(self.__result)

    def __index__(self) -> Any:
        self.__check_result()
        return self.__result.__index__()

    def __len__(self) -> int:
        self.__check_result()
        return len(self.__result)

    def __getitem__(self, key: Any) -> Any:
        self.__check_result()
        return self.__result[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self.__check_result()
        self.__result[key] = value

    def __delitem__(self, key: Any) -> None:
        self.__check_result()
        del self.__result[key]

    def __contains__(self, value: Any) -> bool:
        self.__check_result()
        return value in self.__result

    def __iter__(self) -> Any:
        self.__check_result()
        return iter(self.__result)

    def __reversed__(self) -> Any:
        self.__check_result()
        return reversed(self.__result)

    def __next__(self) -> Any:
        self.__check_result()
        return next(self.__result)

    def __enter__(self) -> Any:
        self.__check_result()
        return self.__result.__enter__()

    def __exit__(self, *args: object, **kwargs: Any) -> bool:
        self.__check_result()
        return self.__result.__exit__(*args, **kwargs)

    def __await__(self) -> Any:
        self.__check_result()
        return self.__result.__await__()

    def __aiter__(self) -> AsyncIterator[Any]:
        self.__check_result()
        return self.__result.__aiter__()

    def __anext__(self) -> Any:
        self.__check_result()
        return self.__result.__anext__()

    def __aenter__(self) -> Any:
        self.__check_result()
        return self.__result.__aenter__()

    def __aexit__(self, *args: object, **kwargs: Any) -> bool:
        self.__check_result()
        return self.__result.__aexit__(*args, **kwargs)

    def __copy__(self) -> Any:
        self.__check_result()
        return copy(self.__result)

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> Any:
        self.__check_result()
        return deepcopy(self.__result, memo)

    def __getstate__(self) -> Any:
        self.__check_result()
        return self.__result.__getstate__()

    def __setstate__(self, state: Any) -> None:
        self.__check_result()
        self.__result = state.__setstate__(state)

    def __reduce__(self) -> Any:
        self.__check_result()
        return self.__result.__reduce__()

    def __reduce_ex__(self, protocol: int) -> Any:
        self.__check_result()
        return self.__result.__reduce_ex__(protocol)

    def __sizeof__(self) -> int:
        self.__check_result()
        return self.__result.__sizeof__()

    def __instancecheck__(self, instance: Any) -> bool:
        self.__check_result()
        return self.__result.__instancecheck__(instance)

    def __subclasscheck__(self, subclass: Any) -> bool:
        self.__check_result()
        return self.__result.__subclasscheck__(subclass)
