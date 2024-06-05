from __future__ import annotations

import inspect
from collections.abc import Hashable
from types import FunctionType, NoneType, UnionType
from typing import TYPE_CHECKING, Any, Generic, Literal, Union, get_args, get_origin

from graphql import Undefined

from undine.dataclasses import DispatchImplementations
from undine.exceptions import (
    FunctionDispatcherImplementationNotFoundError,
    FunctionDispatcherImproperLiteralError,
    FunctionDispatcherNoArgumentAnnotationError,
    FunctionDispatcherNoArgumentsError,
    FunctionDispatcherNonRuntimeProtocolError,
    FunctionDispatcherRegistrationError,
    FunctionDispatcherUnionTypeError,
    FunctionDispatcherUnknownArgumentError,
)
from undine.typing import Lambda, LiteralArg, T

from .reflection import (
    can_be_literal_arg,
    get_instance_name,
    get_signature,
    is_lambda,
    is_not_required_type,
    is_protocol,
    is_required_type,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from undine.typing import DispatchProtocol

__all__ = [
    "FunctionDispatcher",
]


class FunctionDispatcher(Generic[T]):
    """
    A class that holds different implementations for a function
    based on the function's first argument. Different implementations can be added with the `register` method.
    Use implementations by calling the instance with a single positional argument and any number of keyword arguments.
    If no implementation is found, an error will be raised.
    """

    def __init__(self, *, wrapper: Callable[[DispatchProtocol[T]], DispatchProtocol[T]] | None = None) -> None:
        """
        Create a new FunctionDispatcher. Must be added to a variable before use!

        :param wrapper: A function that wraps all implemented functions for performing additional logic.
        """
        self.__name__ = get_instance_name()
        self.implementations: DispatchImplementations[T] = DispatchImplementations()
        self.wrapper = wrapper
        self.default: DispatchProtocol[T] = Undefined  # type: ignore[assignment]

    def __class_getitem__(cls, key: T) -> FunctionDispatcher[T]:
        """Adds typing information when used like this: `foo = FunctionDispatcher[T]()`."""
        return cls  # type: ignore[return-value]

    def __call__(self, value: Any, /, **kwargs: Any) -> T:
        """Find the implementation for the given key and call it with the given keyword arguments."""
        key = self._remove_null(value)
        implementation = self[value]
        return implementation(key, **kwargs)

    def __getitem__(self, original_key: Any) -> DispatchProtocol[T]:  # noqa: C901, PLR0912
        """Find the implementation for the given key."""
        non_null_key = self._remove_null(original_key)
        key = get_origin(non_null_key) or non_null_key

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
            section: dict[Any, DispatchProtocol] = self.implementations.types
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

    def __contains__(self, value: Any) -> bool:
        try:
            self[value]
        except FunctionDispatcherImplementationNotFoundError:
            return False
        return True

    def register(self, func: Callable[..., T]) -> Callable[..., T]:
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

    def _remove_null(self, key: Any) -> Any:
        if is_required_type(key) or is_not_required_type(key):
            return key.__args__[0]

        origin = get_origin(key)
        if origin not in {UnionType, Union}:
            return key

        args = get_args(key)
        if NoneType in args:
            args = tuple(arg for arg in args if arg is not NoneType)

        if len(args) > 1:
            raise FunctionDispatcherUnionTypeError(args=args)

        return args[0]

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

    def _iter_args(self, annotation: Any) -> Generator[tuple[str, Any], None, None]:
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
