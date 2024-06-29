from __future__ import annotations

import inspect
import sys
from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import FrameType, FunctionType

    from undine.typing import T

__all__ = [
    "get_members",
    "get_signature",
]


def get_members(obj: object, type_: type[T]) -> list[tuple[str, T]]:
    """Get memebers of the given object that are instances of the given type."""
    return inspect.getmembers(obj, lambda x: isinstance(x, type_))


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
    don't need to know the globals of the function scope to resolve it.

    :param func: The function to parse.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
    """
    depth += 3  # +1 for this function, +1 for the decorator, +1 for the parent function.
    frame: FrameType = sys._getframe(depth)  # type: ignore[attr-defined]  # noqa: SLF001

    try:
        return inspect.signature(func, eval_str=True, globals=frame.f_globals, locals=frame.f_locals)
    except NameError as error:
        msg = (
            f"Name '{error.name}' is not defined in module '{func.__module__}'. "
            f"Check if it's inside a `if TYPE_CHECKING` block. '{error.name}' needs to be "
            f"available during runtime so that signature of '{func.__name__}' can be inspected."
        )
        raise RuntimeError(msg) from error


def swappable_by_subclassing(obj: T) -> T:
    """
    Makes the decorated class return the most recently
    created direct subclass when it is instantiated.
    """
    orig_init_subclass = obj.__init_subclass__

    def init_subclass(*args: Any, **kwargs: Any) -> None:
        nonlocal obj

        new_subcls: type = obj.__subclasses__()[-1]

        def new(_: type, *_args: Any, **_kwargs: Any) -> T:
            return super(type, new_subcls).__new__(new_subcls)  # type: ignore[arg-type]

        obj.__new__ = new

        return orig_init_subclass(*args, **kwargs)

    obj.__init_subclass__ = init_subclass
    return obj
