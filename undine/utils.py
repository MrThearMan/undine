from __future__ import annotations

import inspect
import sys
from types import FunctionType, NoneType, UnionType
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, get_args, get_origin

from graphql import Undefined

if TYPE_CHECKING:
    from types import FrameType

__all__ = [
    "TypeMapper",
]

TCallable = TypeVar("TCallable")
From = TypeVar("From")
To = TypeVar("To")


class TypeMapper(Generic[From, To]):
    """Maps types or types of values to implementations."""

    def __init__(
        self,
        name: str,
        /,
        default_type: From | Undefined = Undefined,
        wrapper: Callable[[Callable[[From], To]], Callable[[From], To]] | None = None,
        null_hook: Callable[[bool], Callable[[Callable[[From], To]], Callable[[From], To]]] | None = None,
    ) -> None:
        self.name = name
        self.default_type = default_type
        self.wrapper = wrapper
        self.null_hook = null_hook
        self.implementations: dict[From, Callable[[From], To]] = {}

    def __call__(self, key: From) -> To:
        return self[key]

    def __getitem__(self, key: From) -> Callable[[From], To]:
        if key is Undefined:
            msg = "TypeMapper key must be a type or value."
            raise KeyError(msg)

        new_key, nullable = self.handle_nullable(key)
        type_ = self.get_key(new_key)

        try:
            value = self.implementations[type_]
        except KeyError as error:
            for parent_type in type_.__mro__:
                if parent_type in self.implementations:
                    value = self.implementations[parent_type]
                    break
            else:
                msg = f"'{self.name}' doesn't have an implementation for '{type_}' (derived from {key!r})."
                raise KeyError(msg) from error

        return self.null_hook(nullable=nullable)(value)(new_key) if self.null_hook else value(new_key)

    def handle_nullable(self, key: From) -> tuple[type, bool]:
        if get_origin(key) is not UnionType:
            return key, False

        nullable: bool = False
        args = get_args(key)
        if NoneType in args:
            args = tuple(arg for arg in args if arg is not NoneType)
            nullable = True

        if len(args) == 1:
            return args[0], nullable

        # Allow using a default type for union with multiple non-null types.
        if self.default_type is not Undefined:
            return self.default_type, nullable

        msg = f"Union type must have a single non-null type argument, got {args}."
        raise TypeError(msg)

    def __setitem__(self, key: From, value: Callable[[From], To]) -> None:
        if key is Undefined:
            msg = "TypeMapper key cannot be Undefined."
            raise KeyError(msg)

        type_ = self.get_key(key)
        if type is UnionType:
            msg = "A type union cannot be registered."
            raise TypeError(msg)

        self.implementations[type_] = value

    def get_key(self, key: From) -> type:
        origin = get_origin(key) or key
        return type(key) if not isinstance(origin, type) else origin

    def register(self, func: Callable[[From], To]) -> Callable[[From], To]:
        if not isinstance(func, FunctionType):
            msg = "Can only register functions to TypeMapper."
            raise TypeError(msg)

        signature = get_signature(func)
        type_ = next((param.annotation for param in signature.parameters.values()), Undefined)
        if type_ is Undefined:
            msg = "Registered function must have at least one argument."
            raise ValueError(msg)
        if type_ is inspect.Parameter.empty:
            msg = "Registered function's first argument must have a type annotation."
            raise ValueError(msg)

        origin = get_origin(type_)
        keys: list[type] = (
            [origin or type_]
            if origin not in [type, UnionType]
            else [get_origin(arg) or arg for arg in get_args(type_)]
        )

        for key in keys:
            self[key] = self.wrapper(func) if self.wrapper is not None else func
        return func


def get_signature(func: FunctionType, *, level: int = 0) -> inspect.Signature:
    frame: FrameType = sys._getframe(level + 2)  # type: ignore[attr-defined]  # noqa: SLF001
    try:
        return inspect.signature(func, eval_str=True, globals=frame.f_globals, locals=frame.f_locals)
    except NameError as error:
        msg = (
            f"Name '{error.name}' is not defined in module '{func.__module__}'. "
            f"Check if it's inside a `if TYPE_CHECKING` block. The type hint needs to be "
            f"available during runtime so that signature of '{func.__name__}' can be inspected."
        )
        raise RuntimeError(msg) from error
