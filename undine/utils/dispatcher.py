"""
Contains a class for dispatching different registered function calls
based on those registered function's first argument's type.
"""

from __future__ import annotations

import inspect
import sys
from types import FunctionType, NoneType, UnionType
from typing import Any, Callable, Generic, Union, get_args, get_origin

from graphql import Undefined

from undine.errors.exceptions import TypeDispatcherError
from undine.parsers import parse_return_annotation
from undine.typing import DispatchWrapper, From, To

from .reflection import get_signature

__all__ = [
    "TypeDispatcher",
]


class TypeDispatcher(Generic[From, To]):
    """
    A dispatcher that holds registered implementations for a function
    based on the function's first argument's type.

    When called, the dispatcher will find the implementation that matches
    with the first argument's type and call it with the given arguments.
    If no exact match is found, the dispatcher will try look for
    and implementation from the argument types method resolution order.
    If no implementation is found, the dispatcher will try to find
    a default implementation, and failing that, raise a TypeDispatcherError.

    Different implementations can be added with the `register` method.
    """

    def __init__(
        self,
        *,
        union_default: From = Undefined,
        wrapper: DispatchWrapper[From, To] | None = None,
    ) -> None:
        """
        Initialize the dispatcher.

        :param union_default: The default implementation to use for unions that have
                              more than one non-null type.
        :param wrapper: A function that wraps all implementated functions for
                        performing additional logic.
        """
        self.name = self._get_name()
        self.union_default = union_default
        self.wrapper = wrapper
        self.default = Undefined
        self.implementations: dict[From, Callable[[From], To]] = {}

    def __class_getitem__(cls, key: tuple[From, To]) -> TypeDispatcher[From, To]:
        """Adds typing information when instantiating the class."""
        return cls  # type: ignore[return-value]

    def __call__(self, key: From, **kwargs: Any) -> To:
        """Find the implementation for the given key and call it with the given arguments."""
        return_nullable = kwargs.pop("return_nullable", False)
        if key is Undefined:
            msg = "TypeDispatcher key must be a type or value."
            raise TypeDispatcherError(msg)

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
                    msg = f"'{self.name}' doesn't contain an implementation for '{type_}' ({key})."
                    raise TypeDispatcherError(msg) from error

        result = value(new_key, **kwargs)
        if return_nullable:
            return result, nullable
        return result

    def get_key(self, key: Any) -> type:
        origin = get_origin(key) or key
        return type(key) if not isinstance(origin, type) else origin

    def handle_nullable(self, key: From) -> tuple[type, bool]:
        """For types like Union[str, None], return 'str, True'."""
        annotation = key
        origin = get_origin(key)
        if isinstance(key, FunctionType):
            annotation = parse_return_annotation(key)
            origin = get_origin(annotation)

        if origin is not UnionType:
            return key, False

        nullable: bool = False
        args = get_args(annotation)
        if NoneType in args:
            args = tuple(arg for arg in args if arg is not NoneType)
            nullable = True

        if len(args) == 1:
            return key if isinstance(key, FunctionType) else args[0], nullable

        # Allow using a default type for union with multiple non-null types.
        if self.union_default is not Undefined:
            return self.union_default, nullable

        msg = f"Union type must have a single non-null type argument, got {args}."
        raise TypeDispatcherError(msg)

    def register(self, func: Callable[[From], To]) -> Callable[[From], To]:
        """
        Register the given function as an implementation for its
        first argument's type in the TypeDispatcher.

        If the first argument's type is 'Any', the function will be
        registered as the default implementation.

        If the first argument's type is a Union, the function will be
        registered as the implementation for all the types in the Union.
        """
        if not isinstance(func, FunctionType):
            msg = f"Can only register functions with '{self.name}'."
            raise TypeDispatcherError(msg)

        type_ = self.first_param_type(func, depth=1)
        if type_ is Any:
            self.default = self.wrapper(func) if self.wrapper is not None else func
            return func

        origin = get_origin(type_)
        keys: list[type] = (
            [origin or type_]
            if origin not in [type, UnionType, Union]
            else [get_origin(arg) or arg for arg in get_args(type_)]
        )

        for key in keys:
            if key is Undefined:
                msg = f"'{self.name}' cannot register an implmentation for 'Undefined'."
                raise TypeDispatcherError(msg)

            key_ = self.get_key(key)
            if key_ is UnionType:
                msg = f"'{self.name}' cannot register an implementation for a Union member: {key}."
                raise TypeDispatcherError(msg)

            self.implementations[key_] = self.wrapper(func) if self.wrapper is not None else func

        return func

    def first_param_type(self, func: FunctionType, *, depth: int = 0) -> type:
        """Get the type of the first parameter of the given function."""
        sig = get_signature(func, depth=depth + 1)

        type_ = next((param.annotation for param in sig.parameters.values()), Undefined)
        if type_ is Undefined:
            msg = "Registered function must have at least one argument."
            raise TypeDispatcherError(msg)
        if type_ is inspect.Parameter.empty:
            msg = "Registered function's first argument must have a type annotation."
            raise TypeDispatcherError(msg)
        return type_

    def _get_name(self) -> str:
        """
        Perform some python black magic to find the name of the variable
        to which the TypeDispatcher is begin assigned to.

        Note: This only works if the TypeDispatcher initializer is called on the
        same line as the variable for it's instance is defined on.
        """
        if hasattr(self, "name"):
            return self.name
        frame = sys._getframe(2)
        source = inspect.findsource(frame)[0]
        line = source[frame.f_lineno - 1]
        definition = line.split("=", maxsplit=1)[0]
        return definition.split(":", maxsplit=1)[0].strip()
