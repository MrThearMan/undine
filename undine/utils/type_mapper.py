from __future__ import annotations

import inspect
import sys
from types import FunctionType, NoneType, UnionType
from typing import Any, Callable, Generic, TypeVar, get_args, get_origin

from graphql import Undefined, UndefinedType

from undine.parsers.parse_annotations import parse_parameters

__all__ = [
    "TypeMapper",
]


From = TypeVar("From")
To = TypeVar("To")


class TypeMapper(Generic[From, To]):
    """Maps types or types of values to implementations."""

    def __init__(
        self,
        /,
        union_default: From | UndefinedType = Undefined,
        wrapper: Callable[[Callable[[From], To]], Callable[[From], To]] | None = None,
        process_nullable: Callable[[To, bool], To] | None = None,
    ) -> None:
        self.name = self._get_name()
        self.union_default = union_default
        self.wrapper = wrapper
        self.process_nullable = process_nullable
        self.default = Undefined
        self.implementations: dict[From, Callable[[From], To]] = {}

    def __class_getitem__(cls, key: tuple[From, To]) -> TypeMapper[From, To]:
        return cls  # type: ignore[return-value]

    def __call__(self, key: From, **kwargs: Any) -> To:
        if key is Undefined:
            msg = "TypeMapper key must be a type or value."
            raise KeyError(msg)

        new_key, nullable = self.handle_nullable(key)
        type_ = self.get_key(new_key)

        try:
            value = self.implementations[type_]
        except KeyError as error:
            for parent_type in type_.__mro__[1:]:
                if parent_type in self.implementations:
                    value = self.implementations[parent_type]
                    break
            else:
                if self.default is not Undefined:
                    value = self.default
                else:
                    msg = f"'{self.name}' doesn't contain an implementation for '{type_}' (derived from {key!r})."
                    raise KeyError(msg) from error

        result = value(new_key, **kwargs)
        if self.process_nullable:
            return self.process_nullable(result, nullable=nullable)
        return result

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

    def handle_nullable(self, key: From) -> tuple[type, bool]:
        """For types like Union[str, None], return 'str, True'."""
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
        if self.union_default is not Undefined:
            return self.union_default, nullable

        msg = f"Union type must have a single non-null type argument, got {args}."
        raise TypeError(msg)

    def register(self, func: Callable[[From], To]) -> Callable[[From], To]:
        if not isinstance(func, FunctionType):
            msg = f"Can only register functions with '{self.name}'."
            raise TypeError(msg)

        type_ = self.first_param_type(func)
        if type_ is Any:
            self.default = func
            return func

        origin = get_origin(type_)
        keys: list[type] = (
            [origin or type_]
            if origin not in [type, UnionType]
            else [get_origin(arg) or arg for arg in get_args(type_)]
        )

        for key in keys:
            self[key] = self.wrapper(func) if self.wrapper is not None else func
        return func

    def first_param_type(self, func: FunctionType, *, level: int = 0) -> type:
        """Get function first parameter type. Used by TypeMapper."""
        params = parse_parameters(func, level=level + 1)
        type_ = next((param.annotation for param in params), Undefined)
        if type_ is Undefined:
            msg = "Registered function must have at least one argument."
            raise ValueError(msg)
        if type_ is inspect.Parameter.empty:
            msg = "Registered function's first argument must have a type annotation."
            raise ValueError(msg)
        return type_

    def _get_name(self) -> str:
        """
        Perform some python black magic to ind the name of the variable
        to which the TypeMapper is begin assigned to.
        """
        if hasattr(self, "name"):
            return self.name
        frame = sys._getframe(2)  # noqa: SLF001
        source = inspect.findsource(frame)[0]
        line = source[frame.f_lineno - 1]
        definition = line.split("=", maxsplit=1)[0]
        return definition.split(":", maxsplit=1)[0].strip()
