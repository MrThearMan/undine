from __future__ import annotations

import inspect
from collections.abc import Generator, Hashable
from types import FunctionType, NoneType, UnionType
from typing import Any, Callable, Generic, Literal, Union, get_args, get_origin

from graphql import Undefined

from undine.dataclasses import DispatchImplementations
from undine.errors.exceptions import (
    FunctionDispatcherImplementationNotFoundError,
    FunctionDispatcherImproperLiteralError,
    FunctionDispatcherNoArgumentAnnotationError,
    FunctionDispatcherNoArgumentsError,
    FunctionDispatcherNonRuntimeProtocolError,
    FunctionDispatcherRegistrationError,
    FunctionDispatcherUnionTypeError,
    FunctionDispatcherUnknownArgumentError,
)
from undine.typing import DispatchCategory, DispatchProtocol, DispatchWrapper, From, Lambda, LiteralArg, To

from .reflection import (
    can_be_literal_arg,
    get_instance_name,
    get_signature,
    is_lambda,
    is_not_required_type,
    is_protocol,
    is_required_type,
)

__all__ = [
    "FunctionDispatcher",
]


class FunctionDispatcher(Generic[From, To]):
    """
    A class that holds different implementations for a function
    based on the function's first argument. Different implementations can be added with the `register` method.
    Use implementations by calling the instance with a single positional argument and any number of keyword arguments.
    If no implementation is found, an error will be raised.
    """

    def __init__(self, *, wrapper: DispatchWrapper[From, To] | None = None) -> None:
        """
        Create a new FunctionDispatcher. Must be added to a variable before use!

        :param wrapper: A function that wraps all implemented functions for performing additional logic.
        """
        self.__name__ = get_instance_name()
        self.implementations = DispatchImplementations[From, To]()
        self.wrapper = wrapper
        self.default = Undefined

    def __class_getitem__(cls, key: tuple[From, To]) -> FunctionDispatcher[From, To]:
        """Adds typing information when used like this: `foo = FunctionDispatcher[From, To]()`."""
        return cls  # type: ignore[return-value]

    def __call__(self, original_key: From, /, *, return_nullable: bool = False, **kwargs: Any) -> To:
        """Find the implementation for the given key and call it with the given keyword arguments."""
        key, nullable = self._split_nullability(original_key)
        implementation = self[key]
        result = implementation(key, **kwargs)

        if return_nullable:
            return result, nullable

        return result

    def __getitem__(self, original_key: From) -> DispatchProtocol:  # noqa: C901, PLR0912
        """Find the implementation for the given key."""
        key = self._split_nullability(original_key)[0]
        key = get_origin(key) or key

        if is_lambda(key):
            impl = self.implementations.types.get(Lambda)
            if impl is not None:
                return impl

        elif callable(key):
            for proto, impl in self.implementations.protocols.items():
                if isinstance(key, proto):
                    return impl

        elif can_be_literal_arg(key):
            impl = self.implementations.literals.get(key)
            if impl is not None:
                return impl

        if isinstance(key, type):
            section = self.implementations.types
            cls: type = get_origin(key) or key

        else:
            section = self.implementations.instances
            cls = type(key)

            if isinstance(key, Hashable):
                impl = section.get(key)
                if impl is not None:
                    return impl

        for mro_cls in cls.__mro__:
            impl = section.get(mro_cls)
            if impl is not None:
                return impl

        if self.default is not Undefined:
            return self.default

        raise FunctionDispatcherImplementationNotFoundError(name=self.__name__, key=key, cls=cls)

    def register(self, func: Callable[[From], To]) -> Callable[[From], To]:
        """Register the given function as an implementation for its first argument's type."""
        if not isinstance(func, FunctionType):
            raise FunctionDispatcherRegistrationError(name=self.__name__, value=func)

        annotation = self._first_param_type(func, depth=1)

        if annotation is Any:
            self.default = self.wrapper(func) if self.wrapper else func
            return func

        if annotation in {Lambda, type}:
            self.implementations.types[annotation] = self.wrapper(func) if self.wrapper else func
            return func

        if is_protocol(annotation):
            if not annotation._is_runtime_protocol:  # noqa: SLF001
                raise FunctionDispatcherNonRuntimeProtocolError(annotation=annotation)

            self.implementations.protocols[annotation] = self.wrapper(func) if self.wrapper else func
            return func

        origin = get_origin(annotation)

        # Example: "str" or "int"
        if not origin:
            self.implementations.instances[annotation] = self.wrapper(func) if self.wrapper else func
            return func

        for section, arg in self._iter_args(annotation):
            implementations = getattr(self.implementations, section)
            implementations[arg] = self.wrapper(func) if self.wrapper else func

        return func

    def _split_nullability(self, key: From) -> tuple[From, bool]:
        # GraphQL doesn't differentiate between required and non-null...
        if is_required_type(key):
            return key.__args__[0], False

        if is_not_required_type(key):
            return key.__args__[0], True

        origin = get_origin(key)
        if origin not in {UnionType, Union}:
            return key, False

        args = get_args(key)

        nullable = NoneType in args
        if nullable:
            args = tuple(arg for arg in args if arg is not NoneType)

        if len(args) > 1:
            raise FunctionDispatcherUnionTypeError(args=args)

        return args[0], nullable

    def _first_param_type(self, func: FunctionType, *, depth: int = 0) -> Any:
        """Get the type of the first parameter of the given function."""
        sig = get_signature(func, depth=depth + 1)

        try:
            annotation = next(param.annotation for param in sig.parameters.values())
        except StopIteration as error:
            raise FunctionDispatcherNoArgumentsError(func_name=func.__name__, name=self.__name__) from error

        if annotation is inspect.Parameter.empty:
            raise FunctionDispatcherNoArgumentAnnotationError(func_name=func.__name__, name=self.__name__)

        return annotation

    def _iter_args(self, annotation: Any) -> Generator[tuple[DispatchCategory, Any], None, None]:
        origin = get_origin(annotation)

        for arg in get_args(annotation):
            arg_origin = get_origin(arg)

            # Example: "str | int" or "Union[str, int]"
            if origin in {UnionType, Union}:
                if arg_origin is not None:
                    yield from self._iter_args(arg)
                else:
                    yield "instances", arg

            # Example: "type[str]" or "type[str | int]"
            elif origin is type:
                if arg_origin is not None:
                    yield from (("types", ann) for _, ann in self._iter_args(arg))
                else:
                    yield "types", arg

            # Example: Literal["foo", "bar"]
            elif origin is Literal:
                if not isinstance(arg, LiteralArg):
                    raise FunctionDispatcherImproperLiteralError(arg=arg)
                yield "literals", arg

            else:
                raise FunctionDispatcherUnknownArgumentError(annotation=annotation)
