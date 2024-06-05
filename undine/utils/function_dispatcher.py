from __future__ import annotations

import inspect
from types import FunctionType, NoneType, UnionType
from typing import Any, Callable, Generic, Literal, TypeAlias, Union, get_args, get_origin

from graphql import Undefined

from undine.errors.exceptions import FunctionDispatcherError
from undine.typing import DispatchProtocol, From, Lambda, To

from .reflection import get_instance_name, get_signature, is_lambda, is_not_required_type, is_required_type

__all__ = [
    "FunctionDispatcher",
]


# TODO: Support protocols?
DispatchWrapper: TypeAlias = Callable[[DispatchProtocol[From, To]], DispatchProtocol[From, To]]


class FunctionDispatcher(Generic[From, To]):
    """
    A class that holds different implementations for a function
    based on the function's first argument. Different implementations
    can be added with the `register` method.

    When called, FunctionDispatcher will find the implementation that matches
    the given first argument using this strategy:

    1. Look for an implementation that matches the given argument's type.
    2. If functions have been registered with for 'Literal' types, look for an implementation
       that matches the given argument literally (e.g. literal strings).
    3. Look for an implementation whose first argument is in the method resolution order
       (mro) of the given argument's type.
    4. Look for a default implementation (registered function's first argument's type is `Any`).

    If no implementation is found, an error will be raised.
    """

    def __init__(self, *, wrapper: DispatchWrapper[From, To] | None = None, union_default: Any = Undefined) -> None:
        """
        Create a new FunctionDispatcher. Must be added to a variable before use!

        :param union_default: The default implementation to use for unions that have
                              more than one non-null type.
        :param wrapper: A function that wraps all implemented functions for
                        performing additional logic.
        """
        self.__name__ = get_instance_name()
        self.wrapper = wrapper
        self.union_default = union_default
        self.default = Undefined
        self.implementations: dict[From, Callable[[From], To]] = {}
        self.contains_literals = False

    def __class_getitem__(cls, key: tuple[From, To]) -> FunctionDispatcher[From, To]:
        """Adds typing information when used like this: `foo = FunctionDispatcher[From, To]()`."""
        return cls  # type: ignore[return-value]

    def __call__(self, key: From, **kwargs: Any) -> To:
        """Find the implementation for the given key and call it with the given keyword arguments."""
        return_nullable = kwargs.pop("return_nullable", False)
        if key is Undefined:
            msg = "FunctionDispatcher key must be a type or value."
            raise FunctionDispatcherError(msg)

        new_key, nullable = self._handle_nullable(key)
        type_ = self._get_key(new_key)
        value = self._get_implementation(key, type_)
        result = value(new_key, **kwargs)
        if return_nullable:
            return result, nullable
        return result

    def register(self, func: Callable[[From], To]) -> Callable[[From], To]:
        """
        Register the given function as an implementation for its
        first argument's type in the FunctionDispatcher.

        If the first argument's type is 'Any', the function will be
        registered as the default implementation.

        If the first argument's type is a Union, the function will be
        registered as the implementation for all the types in the Union.
        """
        if not isinstance(func, FunctionType):
            msg = f"Can only register functions with '{self.__name__}'. Got {func}."
            raise FunctionDispatcherError(msg)

        type_ = self._first_param_type(func, depth=1)
        if type_ is Any:
            self.default = self.wrapper(func) if self.wrapper is not None else func
            return func

        if type_ is Lambda:
            self.implementations[Lambda] = self.wrapper(func) if self.wrapper is not None else func
            return func

        origin = get_origin(type_)

        if origin is Literal:
            self.contains_literals = True
            for name in get_args(type_):
                self.implementations[name] = self.wrapper(func) if self.wrapper is not None else func
            return func

        keys: list[type] = (
            [origin or type_]
            if origin not in {type, UnionType, Union}
            else [get_origin(arg) or arg for arg in get_args(type_)]
        )

        for key in keys:
            if key is Undefined:
                msg = (
                    f"Cannot register function '{func.__name__}' for '{self.__name__}': "
                    f"First argument type cannot be 'Undefined'."
                )
                raise FunctionDispatcherError(msg)

            key_ = self._get_key(key)
            if key_ is UnionType:
                msg = f"'{self.__name__}' cannot register an implementation for type '{type_}'."
                raise FunctionDispatcherError(msg)

            self.implementations[key_] = self.wrapper(func) if self.wrapper is not None else func

        return func

    def _get_implementation(self, key: From, type_: type) -> Callable[[From], To]:
        value = self.implementations.get(type_, Undefined)
        if value is not Undefined:
            return value

        if self.contains_literals:
            value = self.implementations.get(key, Undefined)
            if value is not Undefined:
                return value

        for parent_type in type_.__mro__[1:]:
            value = self.implementations.get(parent_type, Undefined)
            if value is not Undefined:
                return value

        if self.default is not Undefined:
            return self.default

        msg = f"'{self.__name__}' doesn't contain an implementation for '{type_}' ({key})."
        raise FunctionDispatcherError(msg)

    def _get_key(self, key: Any) -> type:
        if is_lambda(key):
            return Lambda
        origin = get_origin(key) or key
        return type(key) if not isinstance(origin, type) else origin

    def _handle_nullable(self, key: From) -> tuple[Any, bool]:
        """For types like Union[str, None], return 'str, True'."""
        from undine.parsers import parse_return_annotation  # noqa: PLC0415

        if is_lambda(key):
            return key, False

        # GraphQL doesn't differentiate between required and non-null...
        if is_required_type(key):
            result, _nullable = self._handle_nullable(key.__args__[0])
            return result, False

        if is_not_required_type(key):
            result, _nullable = self._handle_nullable(key.__args__[0])
            return result, True

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
        raise FunctionDispatcherError(msg)

    def _first_param_type(self, func: FunctionType, *, depth: int = 0) -> type:
        """Get the type of the first parameter of the given function."""
        sig = get_signature(func, depth=depth + 1)

        try:
            type_ = next(param.annotation for param in sig.parameters.values())
        except StopIteration as error:
            msg = (
                f"Function '{func.__name__}' must have at least one argument "
                f"so that it can be registered for '{self.__name__}'."
            )
            raise FunctionDispatcherError(msg) from error

        if type_ is inspect.Parameter.empty:
            msg = (
                f"Function '{func.__name__}' must have a type hint for its first argument "
                f"so that it can be registered for '{self.__name__}'."
            )
            raise FunctionDispatcherError(msg)
        return type_
