from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeGuard

from django.db import models
from graphql import GraphQLResolveInfo

from undine.settings import undine_settings

from .reflection import get_signature

if TYPE_CHECKING:
    from types import FunctionType

    from graphql import GraphQLFieldResolver

    from undine.typing import RelatedManager

__all__ = [
    "function_resolver",
    "is_pk_property",
    "model_attr_resolver",
]


def model_attr_resolver(*, name: str, many: bool = False) -> GraphQLFieldResolver:
    """Find a model attribute resolver, either for a regular field or a related field."""
    return ModelManyRelatedResolver(name=name) if many else ModelFieldResolver(name=name)


def function_resolver(func: FunctionType) -> GraphQLFieldResolver:
    """
    Find the appropriate resolver for a function based on its signature.
    Leave out the `root` parameter from static functions, and only include the
    `info` parameter if the function has a parameter of the `GraphQLResolveInfo` type.

    Note that the `root` is always the first parameter, and the matching happens
    by it's name, which can be configured with `RESOLVER_ROOT_PARAM_NAME`.
    `self` is always an accepted root parameter name, since it's the convention for methods.
    """
    # Expects signature to be cached. Won't work correctly otherwise.
    sig = get_signature(func)

    root_param: str | None = None
    info_param: str | None = None
    for i, param in enumerate(sig.parameters.values()):
        if i == 0 and param.name in ("self", undine_settings.RESOLVER_ROOT_PARAM_NAME):
            root_param = param.name

        elif is_graphql_resolver_info(param.annotation):
            info_param = param.name
            break

    if root_param and info_param:
        return FuncResolverWithRootAndInfo(func=func, root_param=root_param, info_param=info_param)
    if root_param:
        return FuncResolverWithRoot(func=func, root_param=root_param)
    if info_param:
        return FuncResolverWithInfo(func=func, info_param=info_param)

    return FuncResolver(func=func)


@dataclass
class ModelFieldResolver:
    name: str

    def __call__(self, model: models.Model, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        return getattr(model, self.name, None)


@dataclass
class ModelManyRelatedResolver:
    name: str

    def __call__(self, model: models.Model, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        related_manager: RelatedManager = getattr(model, self.name)
        return related_manager.get_queryset()


@dataclass
class FuncResolver:
    func: FunctionType

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        return self.func(**kwargs)


@dataclass
class FuncResolverWithRoot:
    func: FunctionType
    root_param: str

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        kwargs[self.root_param] = root
        return self.func(**kwargs)


@dataclass
class FuncResolverWithInfo:
    func: FunctionType
    info_param: str

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        kwargs[self.info_param] = info
        return self.func(**kwargs)


@dataclass
class FuncResolverWithRootAndInfo:
    func: FunctionType
    root_param: str
    info_param: str

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        kwargs[self.root_param] = root
        kwargs[self.info_param] = info
        return self.func(**kwargs)


def is_graphql_resolver_info(value: Any) -> TypeGuard[GraphQLResolveInfo]:
    """Check is the given value is the GraphQLResolveInfo."""
    return isinstance(value, type) and issubclass(value, GraphQLResolveInfo)


def is_pk_property(value: Any) -> TypeGuard[property]:
    """Check is the given value is the Django Model 'pk' property."""
    return isinstance(value, property) and value.fget == models.Model._get_pk_val  # noqa: SLF001
