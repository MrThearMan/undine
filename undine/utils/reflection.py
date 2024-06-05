from __future__ import annotations

import inspect
import sys
from functools import partial
from types import FunctionType, GenericAlias, LambdaType
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, Protocol, TypeGuard, TypeVar

from graphql import GraphQLResolveInfo

from undine.dataclasses import RootAndInfoParams
from undine.exceptions import FunctionSignatureParsingError
from undine.settings import undine_settings
from undine.typing import GQLInfo, LiteralArg, ParametrizedType

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Hashable, Sequence
    from types import FrameType

    from undine.typing import Lambda


__all__ = [
    "FunctionEqualityWrapper",
    "cache_signature_if_function",
    "can_be_literal_arg",
    "get_instance_name",
    "get_members",
    "get_root_and_info_params",
    "get_signature",
    "get_wrapped_func",
    "has_callable_attribute",
    "is_generic_list",
    "is_lambda",
    "is_not_required_type",
    "is_protocol",
    "is_required_type",
    "is_same_func",
    "is_subclass",
    "reverse_enumerate",
]


try:  # pragma: no cover
    from typing import is_protocol
except ImportError:  # pragma: no cover

    def is_protocol(tp: type, /) -> bool:
        """Check if the given type is a Protocol."""
        return isinstance(tp, type) and getattr(tp, "_is_protocol", False) and tp != Protocol


T = TypeVar("T")
P = ParamSpec("P")
TType = TypeVar("TType", bound=type)


def get_members(obj: object, type_: type[T]) -> dict[str, T]:
    """Get members of the given object that are instances of the given type."""
    return dict(inspect.getmembers(obj, lambda x: isinstance(x, type_)))


def get_wrapped_func(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Get the inner function of a partial function, classmethod, staticmethod, property,
    or a function wrapped with `functools.wraps`.
    """
    while True:
        if hasattr(func, "__wrapped__"):  # Wrapped with functools.wraps
            func = func.__wrapped__
            continue
        if isinstance(func, partial):
            func = func.func
            continue
        if inspect.ismethod(func) and hasattr(func, "__func__"):
            func = func.__func__
            continue
        if isinstance(func, property):
            func = func.fget
            continue
        break
    return func


def cache_signature_if_function(value: Callable[..., Any], *, depth: int = 0) -> Callable[..., Any]:
    """
    Cache signature of the given value if it's a known function type.
    This allows calling `get_signature` later without knowing the function globals or locals.

    :param value: The value to cache the signature of.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
    :returns: The "unwrapped" function, if it was a know function type, otherwise the value as is.
    """
    value = get_wrapped_func(value)
    if isinstance(value, FunctionType):
        get_signature(value, depth=depth + 1)
    return value


class _SignatureParser:
    """
    Parse the signature of a function.

    Parsed signatures are cached so that subsequent queries for the same function
    don't need to know the globals or locals of the function scope to resolve it.
    """

    def __init__(self) -> None:
        self.cache: dict[FunctionType | Callable[..., Any], inspect.Signature] = {}

    def __call__(self, func: FunctionType | Callable[..., Any], /, *, depth: int = 0) -> inspect.Signature:
        """
        Parse the signature

        :param func: The function to parse.
        :param depth: How many function calls deep is the code calling this method compared to the parsed function?
        """
        if func in self.cache:
            return self.cache[func]

        depth += 1
        frame: FrameType = sys._getframe(depth)

        # Add some common stuff to globals so that we don't encounter as many NameErrors
        # when parsing signatures if these type hints are in a `TYPE_CHECKING` block.
        extra_globals: dict[str, Any] = {
            "GraphQLResolveInfo": GraphQLResolveInfo,
            "GQLInfo": GQLInfo,
            "Any": Any,
        }

        frame_locals: dict[str, Any] = frame.f_locals
        frame_globals: dict[str, Any] = frame.f_globals | extra_globals

        # Check if previous frames are in the same file and collect their locals.
        depth += 1
        prev_frame: FrameType = sys._getframe(depth)
        while prev_frame.f_code.co_filename == frame.f_code.co_filename:
            frame_locals = prev_frame.f_locals | frame_locals  # order matters!
            depth += 1
            prev_frame = sys._getframe(depth)

        try:
            sig = inspect.signature(func, eval_str=True, globals=frame_globals, locals=frame_locals)
        except NameError as error:
            raise FunctionSignatureParsingError(name=error.name, func=func) from error

        self.cache[func] = sig
        return sig


get_signature = _SignatureParser()


def has_callable_attribute(obj: object, name: str) -> bool:
    """Check if the given object has a callable attribute with the given name."""
    return hasattr(obj, name) and callable(getattr(obj, name))


def is_subclass(obj: object, cls: TType) -> TypeGuard[TType]:
    """Check if the given object is a subclass of the given class."""
    return isinstance(obj, type) and issubclass(obj, cls)  # type: ignore[arg-type]


def is_generic_list(type_: type) -> TypeGuard[GenericAlias]:
    """Check if the given type is a generic list, i.e., `list[str]`."""
    return isinstance(type_, GenericAlias) and issubclass(type_.__origin__, list)  # type: ignore[arg-type]


def is_lambda(func: Callable[..., Any]) -> TypeGuard[Lambda]:
    """Check if the given function is a lambda function."""
    return isinstance(func, LambdaType) and func.__name__ == "<lambda>"


def is_required_type(type_: Any) -> bool:
    """Check if the given type is a TypedDict `Required` type."""
    return isinstance(type_, ParametrizedType) and type_.__origin__._name == "Required"  # type: ignore[misc]  # noqa: SLF001


def is_not_required_type(type_: Any) -> bool:
    """Check if the given type is a TypedDict `Required` type."""
    return isinstance(type_, ParametrizedType) and type_.__origin__._name == "NotRequired"  # type: ignore[misc]  # noqa: SLF001


def is_same_func(func_1: FunctionType | Callable[..., Any], func_2: FunctionType | Callable[..., Any], /) -> bool:
    """
    Check if the given functions are the same function.
    Handles partial functions and functions wrapped with `functools.wraps`.
    """
    return get_wrapped_func(func_1) == get_wrapped_func(func_2)


def can_be_literal_arg(key: Any) -> TypeGuard[LiteralArg]:
    return isinstance(key, LiteralArg)


def get_instance_name() -> str:
    """
    Perform some python black magic to find the name of the variable
    to which an instance of a class is being assigned to.
    Should be used in the '__init__' method.

    Note: This only works if the instance initializer is called on the
    same line as the variable for it's defined to.
    """
    frame = sys._getframe(2)
    source = inspect.findsource(frame)[0]
    line = source[frame.f_lineno - 1]
    definition = line.split("=", maxsplit=1)[0]
    return definition.split(":", maxsplit=1)[0].strip()


class FunctionEqualityWrapper(Generic[T]):
    """
    Adds equality checks for a function based on the provided context.
    Function is equal to another function if it's also wrapped with this class
    and the provided contexts are equal.
    """

    def __init__(self, func: Callable[[], T], context: Hashable) -> None:
        self.func = func
        self.context = context

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.context == other.context

    def __hash__(self) -> int:
        return hash(self.context)

    def __call__(self) -> T:
        return self.func()


def get_root_and_info_params(func: FunctionType | Callable[..., Any], *, depth: int = 0) -> RootAndInfoParams:
    """
    Inspect the function signature to figure out which parameters are
    the root and info parameters of a GraphQL resolver function, if any.

    `root_param` is the first parameter of the function if it's named `self`, `cls`,
    or the name configured with the `RESOLVER_ROOT_PARAM_NAME` setting (`root` by default).

    `info_param` is annotated as `GraphQLResolveInfo` or `GQLInfo` if it exists,
    and is usually the second parameter of the function, but can also be in any
    other position other than first.
    """
    sig = get_signature(func, depth=depth + 1)

    root_param: str | None = None
    info_param: str | None = None
    for i, param in enumerate(sig.parameters.values()):
        if i == 0 and param.name in {"self", "cls", undine_settings.RESOLVER_ROOT_PARAM_NAME}:
            root_param = param.name

        elif param.annotation in {GraphQLResolveInfo, GQLInfo}:
            info_param = param.name
            break

    return RootAndInfoParams(root_param=root_param, info_param=info_param)


def reverse_enumerate(sequence: Sequence[T]) -> Generator[tuple[int, T], None, None]:
    """
    Enumerate the given sequence in reverse order.
    Using this allows using `.pop(index)` on the sequence to remove the iterated item if needed.

    >>> x = ["a", "b", "c"]
    >>> for i, item in reverse_enumerate(x):
    >>>     x.pop(i)
    """
    for index in range(len(sequence) - 1, -1, -1):
        yield index, sequence[index]
