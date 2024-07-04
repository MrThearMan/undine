from __future__ import annotations

import inspect
import sys
from functools import partial, wraps
from types import FunctionType
from typing import TYPE_CHECKING, Any

from graphql import GraphQLResolveInfo

from undine.errors import FuntionSignatureParsingError

if TYPE_CHECKING:
    from types import FrameType

    from undine.typing import T

__all__ = [
    "cache_signature",
    "get_members",
    "get_signature",
    "get_wrapped",
    "swappable_by_subclassing",
]


def get_members(obj: object, type_: type[T]) -> list[tuple[str, T]]:
    """Get memebers of the given object that are instances of the given type."""
    return inspect.getmembers(obj, lambda x: isinstance(x, type_))


def get_wrapped(func: partial) -> FunctionType:
    """Get the inner function of a partial function or one wrapped with `functools.wraps`."""
    while True:
        if hasattr(func, "__wrapped__"):  # Wrapped with functools.wraps
            func = func.__wrapped__
            continue
        if isinstance(func, partial):
            func = func.func
            continue
        break
    return func


def cache_signature(value: T, *, depth: int = 0) -> T:
    """
    Cache signature of the given value if it's a known function type.
    This allows calling `get_signature` later without knowing the function globals or locals.

    :param value: The value to cache the signature of.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
    :returns: The value as is.
    """
    if isinstance(value, partial):
        value = get_wrapped(value)
    if isinstance(value, (classmethod, staticmethod)):
        value = value.__func__
    if isinstance(value, property):
        value = value.fget
    if isinstance(value, FunctionType):
        get_signature(value, depth=depth + 1)
    return value


def _cache_signatures(wrapped_func: T) -> T:
    """Cache signatured by the given function, ignoring any other arguments."""
    _cache: dict[FunctionType, inspect.Signature] = {}

    @wraps(wrapped_func)
    def wrapper(func: FunctionType, *args: Any, **kwargs: Any) -> Any:
        if func not in _cache:
            _cache[func] = wrapped_func(func, *args, **kwargs)
        return _cache[func]

    wrapper.cache = _cache
    return wrapper  # type: ignore[return-value]


@_cache_signatures
def get_signature(func: FunctionType, *, depth: int = 0) -> inspect.Signature:
    """
    Parse the signature of a function.

    Parsed signatures are cached so that subsequent queries for the same function
    don't need to know the globals or locals of the function scope to resolve it.

    :param func: The function to parse.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
    """
    # Increase depth by 1 for this function and 1 for the decorator
    # so that depth counting starts from the caller function.
    frame: FrameType = sys._getframe(depth + 2)
    # Add some common stuff to frame globals so that we don't encounter so many NameErrors
    # when parsing signatures if these type hints are in a `TYPE_CHECKING` block.
    frame_globals = frame.f_globals | {
        "GraphQLResolveInfo": GraphQLResolveInfo,
        "Any": Any,
    }
    try:
        return inspect.signature(func, eval_str=True, globals=frame_globals, locals=frame.f_locals)
    except NameError as error:
        raise FuntionSignatureParsingError(name=error.name, func=func) from error


def swappable_by_subclassing(cls: T) -> T:
    """
    Decorated class will return the most recently
    created direct subclass when it is instantiated.

    Class should have a `__init__` method(?),
    and should not have a `__new__` method.
    """
    orig_init_subclass = cls.__init_subclass__

    def init_subclass(*args: Any, **kwargs: Any) -> None:
        nonlocal cls

        new_subcls: type = cls.__subclasses__()[-1]

        def new(_: type, *_args: Any, **_kwargs: Any) -> T:
            return super(type, new_subcls).__new__(new_subcls)  # type: ignore[arg-type]

        cls.__new__ = new

        return orig_init_subclass(*args, **kwargs)

    cls.__init_subclass__ = init_subclass
    return cls
